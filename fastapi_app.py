"""FastAPI adapter for Veyntara AI.

Keeps the existing frontend routes and business logic. The web app continues to
use veyntara_web.db; the legacy veyntara.db is not opened or migrated here.
"""
from __future__ import annotations
from starlette.types import ASGIApp, Receive, Scope, Send
import hmac
import json
import secrets
import sqlite3
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, ValidationError

import web_app as core

PROJECT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = PROJECT_DIR / "frontend"
MAX_BODY_BYTES = core.MAX_BODY_BYTES


class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=10, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=10, max_length=128)


class ExperimentCreateRequest(BaseModel):
    assumption_id: int = Field(gt=0)
    experiment: str = Field(min_length=1)
    success_metric: str = Field(min_length=1)
    estimated_cost: float | None = Field(default=None, ge=0)
    duration: str = Field(min_length=1)
    planned_sample_size: int | None = Field(default=None, gt=0)


class ExperimentResultRequest(BaseModel):
    result: str
    observations: str = Field(min_length=1)
    sample_size: int | None = Field(default=None, ge=0)
    successes: int | None = Field(default=None, ge=0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not (FRONTEND_DIR / "index.html").is_file():
        raise RuntimeError("Frontend files are missing. Expected frontend/index.html.")
    core.init_web_database()
    yield

class SecurityMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")

        if content_length:
            try:
                if int(content_length) > MAX_BODY_BYTES:
                    await self.reject(send, 413, "Request body is too large.")
                    return
            except ValueError:
                await self.reject(send, 400, "Invalid request length.")
                return

        body_events = []
        total_size = 0

        while True:
            event = await receive()
            body_events.append(event)

            if event["type"] == "http.request":
                total_size += len(event.get("body", b""))

                if total_size > MAX_BODY_BYTES:
                    await self.reject(send, 413, "Request body is too large.")
                    return

                if not event.get("more_body", False):
                    break

            elif event["type"] == "http.disconnect":
                return

        async def replay_receive():
            if body_events:
                return body_events.pop(0)
            return await receive()

        await self.app(scope, replay_receive, send)

    async def reject(self, send: Send, status: int, message: str):
        body = json.dumps({"error": message}).encode("utf-8")

        await send({
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
                (b"cache-control", b"no-store"),
            ],
        })

        await send({
            "type": "http.response.body",
            "body": body,
        })



app = FastAPI(
    title="Veyntara AI API",
    description="API for Veyntara AI business validation, assumptions, and experiments.",
    version="1.0.0",
    lifespan=lifespan,
)


app.add_middleware(SecurityMiddleware)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return JSONResponse(status_code=exc.status_code, content={"error": detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = []
    for error in exc.errors():
        loc = [str(part) for part in error.get("loc", ()) if part not in ("body",)]
        details.append({"field": ".".join(loc), "message": error.get("msg", "Invalid value.")})
    return JSONResponse(
        status_code=422,
        content={"error": "Please check the submitted fields.", "details": details},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    print(f"[api] Unhandled request failure: {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "The request could not be completed. Check the PowerShell server log before retrying."},
    )


ALLOWED_ORIGINS = {
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://172.20.10.7:5500",
}


def origin_is_allowed(request: Request) -> bool:
    origin = request.headers.get("origin")
    return origin in ALLOWED_ORIGINS


def current_user(request: Request) -> dict[str, Any] | None:
    return core.get_session_user(request)


def require_user(request: Request) -> dict[str, Any]:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Please log in again.")
    return user


def error_response(status: int, message: str, **extra):
    return JSONResponse(status_code=status, content={"error": message, **extra})


def set_session_cookie(response: Response, token: str):
    response.set_cookie(
        key=core.COOKIE_NAME,
        value=token,
        max_age=core.SESSION_SECONDS,
        httponly=True,
        samesite="strict",
        secure=False,  # local HTTP development; use HTTPS + secure=True when deployed
        path="/",
    )


def clear_session_cookie(response: Response):
    response.delete_cookie(
        key=core.COOKIE_NAME,
        httponly=True,
        samesite="strict",
        secure=False,
        path="/",
    )


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "database": "separate web database",
        "message": "Health check does not call AI or write business records.",
    }


@app.get("/api/me")
def me(request: Request):
    user = current_user(request)
    if not user:
        return error_response(401, "Not logged in.")
    return {"user": user}


@app.get("/api/businesses")
def businesses(user: dict = Depends(require_user)):
    return {"businesses": core.get_business_summary(user["id"])}


@app.get("/api/businesses/{business_id}")
def business_detail(business_id: int, user: dict = Depends(require_user)):
    business = core.get_business_detail(user["id"], business_id)
    if not business:
        return error_response(404, "Business not found.")
    return {"business": business}


@app.post("/api/signup")
def signup(payload: SignupRequest, request: Request, response: Response):
    name = payload.name.strip()
    email = payload.email.strip().lower()
    password = payload.password
    if not origin_is_allowed(request):
        return error_response(403, "Request origin rejected.")
    if not name:
        return error_response(400, "Enter a name (up to 100 characters).")
    if not email or "@" not in email:
        return error_response(400, "Enter a valid email address.")

    with core.connect() as con:
        salt, digest = core.hash_password(password)
        try:
            cur = con.execute(
                "INSERT INTO web_users(name,email,password_salt,password_hash,created_at) VALUES(?,?,?,?,?)",
                (name, email, salt, digest, int(time.time())),
            )
            user_id = cur.lastrowid
        except sqlite3.IntegrityError:
            return error_response(409, "An account with this email already exists. Log in instead.")
        user_row = con.execute(
            "SELECT id,name,email FROM web_users WHERE id=?", (user_id,)
        ).fetchone()
        token = secrets.token_urlsafe(32)
        con.execute(
            "INSERT INTO web_sessions(token_hash,user_id,expires_at) VALUES(?,?,?)",
            (core.token_digest(token), user_id, int(time.time()) + core.SESSION_SECONDS),
        )
        con.commit()

    set_session_cookie(response, token)
    return {"user": core.public_user(user_row)}


@app.post("/api/login")
def login(payload: LoginRequest, request: Request, response: Response):
    if not origin_is_allowed(request):
        return error_response(403, "Request origin rejected.")

    email = payload.email.strip().lower()
    with core.connect() as con:
        row = con.execute(
            "SELECT * FROM web_users WHERE email=? COLLATE NOCASE", (email,)
        ).fetchone()
        if not row:
            return error_response(401, "Email or password is incorrect.")
        _, candidate = core.hash_password(payload.password, bytes(row["password_salt"]))
        if not hmac.compare_digest(candidate, bytes(row["password_hash"])):
            return error_response(401, "Email or password is incorrect.")
        user_row = con.execute(
            "SELECT id,name,email FROM web_users WHERE id=?", (row["id"],)
        ).fetchone()
        token = secrets.token_urlsafe(32)
        con.execute(
            "INSERT INTO web_sessions(token_hash,user_id,expires_at) VALUES(?,?,?)",
            (core.token_digest(token), row["id"], int(time.time()) + core.SESSION_SECONDS),
        )
        con.commit()

    set_session_cookie(response, token)
    return {"user": core.public_user(user_row)}


@app.post("/api/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(core.COOKIE_NAME)
    if not origin_is_allowed(request):
        return error_response(403, "Request origin rejected.")

    if token:
        with core.connect() as con:
            con.execute(
                "DELETE FROM web_sessions WHERE token_hash=?", (core.token_digest(token),)
            )
            con.commit()
    clear_session_cookie(response)
    return {"ok": True}


@app.post("/api/validate")
def validate_business(
    request: Request,
    payload: core.BusinessProfile,
    user: dict = Depends(require_user),
):
    if not origin_is_allowed(request):
        return error_response(403, "Request origin rejected.")
    try:
        result = core.run_validation(user["id"], payload.model_dump())
        return result
    except core.ExistingBusiness as exc:
        return error_response(409, f"EXISTING_BUSINESS:{exc.business_id}")
    except ValidationError as exc:
        return error_response(
            422,
            "Please check the submitted fields.",
            details=[
                {"field": ".".join(map(str, item["loc"])), "message": item["msg"]}
                for item in exc.errors()
            ],
        )
    except ValueError as exc:
        return error_response(400, str(exc) or "Invalid request.")
    except Exception as exc:
        print(f"[api] Validation failed: {type(exc).__name__}: {exc}")
        return error_response(500, "Analysis could not be completed. Check the PowerShell server log.")


@app.post("/api/businesses/{business_id}/experiments/{experiment_id}/result")
def record_experiment_result(
    business_id: int,
    experiment_id: int,
    request: Request,
    payload: ExperimentResultRequest,
    user: dict = Depends(require_user),
):
    if not origin_is_allowed(request):
        return error_response(403, "Request origin rejected.")
    if not core.get_owned_business(user["id"], business_id):
        return error_response(404, "Business not found.")
    if payload.result not in ("Supports", "Contradicts", "Unclear") or not payload.observations.strip():
        return error_response(400, "Choose an outcome and enter observations.")
    if (
        payload.sample_size is not None
        and payload.successes is not None
        and payload.successes > payload.sample_size
    ):
        return error_response(400, "Successful outcomes cannot exceed the sample size.")

    with core.connect() as con:
        exp = con.execute(
            "SELECT id FROM experiments WHERE id=? AND business_id=?",
            (experiment_id, business_id),
        ).fetchone()
        if not exp:
            return error_response(404, "Experiment not found.")
        con.execute(
            """UPDATE experiments
               SET result=?,observations=?,sample_size=?,successes=?,status='completed'
               WHERE id=?""",
            (
                payload.result,
                payload.observations.strip(),
                payload.sample_size,
                payload.successes,
                experiment_id,
            ),
        )
        con.commit()
    return {"ok": True}


@app.post("/api/businesses/{business_id}/experiments")
def create_experiment(
    business_id: int,
    request: Request,
    payload: ExperimentCreateRequest,
    user: dict = Depends(require_user),
):
    if not origin_is_allowed(request):
        return error_response(403, "Request origin rejected.")
    business = core.get_owned_business(user["id"], business_id)
    if not business:
        return error_response(404, "Business not found.")
    with core.connect() as con:
        assumption = con.execute(
            "SELECT id,statement FROM assumptions WHERE id=? AND business_id=?",
            (payload.assumption_id, business_id),
        ).fetchone()
    if not assumption:
        return error_response(400, "Choose an assumption belonging to this business.")
    experiment = core.Experiment(
        assumption=assumption["statement"],
        experiment=payload.experiment.strip(),
        success_metric=payload.success_metric.strip(),
        estimated_cost=payload.estimated_cost,
        duration=payload.duration.strip(),
        planned_sample_size=payload.planned_sample_size,
    )
    if not experiment.experiment or not experiment.success_metric or not experiment.duration:
        return error_response(400, "Experiment, success metric, and duration are required.")
    experiment_id = core.save_experiment(business_id, payload.assumption_id, experiment, None)
    return {"ok": True, "experiment_id": experiment_id}


@app.get("/", include_in_schema=False)
def frontend_index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/styles.css", include_in_schema=False)
def frontend_styles():
    return FileResponse(FRONTEND_DIR / "styles.css", media_type="text/css")


@app.get("/script.js", include_in_schema=False)
def frontend_script():
    return FileResponse(FRONTEND_DIR / "script.js", media_type="application/javascript")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("fastapi_app:app", host="127.0.0.1", port=5500, reload=False)
