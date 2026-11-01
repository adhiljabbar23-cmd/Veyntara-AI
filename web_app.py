"""Authenticated, local-only web adapter for Veyntara AI.

IMPORTANT: this web UI uses veyntara_web.db, not the existing veyntara.db.
"""
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from pydantic import ValidationError

import database
from agent import ask_ai
from decision import evaluate_all_assumptions, make_decision
from database import save_assumption, update_assumption_evaluation, save_experiment
from experiments import generate_experiment
from models import BusinessProfile, AssumptionList, EvidenceEvaluation, Experiment
from research import evaluate_evidence

PROJECT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = PROJECT_DIR / "frontend"
WEB_DB_PATH = PROJECT_DIR / "veyntara_web.db"
HOST = "0.0.0.0"
PORT = 5500
MAX_BODY_BYTES = 32_000
SESSION_SECONDS = 60 * 60 * 24 * 7
COOKIE_NAME = "veyntara_session"

# Redirect the existing persistence helpers to the separate web database.
database.DB_NAME = str(WEB_DB_PATH)


def connect():
    conn = sqlite3.connect(str(WEB_DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_web_database():
    # Initializes only veyntara_web.db. Never initializes or migrates veyntara.db.
    database.initialize_database()
    with connect() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS web_users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_salt BLOB NOT NULL,
            password_hash BLOB NOT NULL,
            created_at INTEGER NOT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS web_sessions(
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expires_at INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES web_users(id) ON DELETE CASCADE
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS web_business_owners(
            business_id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            assessment_json TEXT,
            created_at INTEGER NOT NULL,
            FOREIGN KEY(business_id) REFERENCES businesses(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES web_users(id) ON DELETE CASCADE
        )""")
        con.execute("CREATE INDEX IF NOT EXISTS idx_web_owner_user ON web_business_owners(user_id)")
        con.commit()


def json_safe(value):
    if hasattr(value, "model_dump"):
        return json_safe(value.model_dump())
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return salt, digest


def token_digest(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def public_user(row):
    return {"id": row["id"], "name": row["name"], "email": row["email"]}


def get_session_user(handler):
    cookie = handler.headers.get("Cookie", "")
    token = None
    for item in cookie.split(";"):
        key, sep, value = item.strip().partition("=")
        if sep and key == COOKIE_NAME:
            token = value
            break
    if not token:
        return None
    now = int(time.time())
    with connect() as con:
        row = con.execute("""SELECT u.id,u.name,u.email
            FROM web_sessions s JOIN web_users u ON u.id=s.user_id
            WHERE s.token_hash=? AND s.expires_at>?""", (token_digest(token), now)).fetchone()
        con.execute("DELETE FROM web_sessions WHERE expires_at<=?", (now,))
        con.commit()
    return dict(row) if row else None


def json_dump(value):
    return json.dumps(json_safe(value), ensure_ascii=False)


def get_owned_business(user_id, business_id):
    with connect() as con:
        row = con.execute("""SELECT b.*, o.assessment_json
            FROM businesses b JOIN web_business_owners o ON o.business_id=b.id
            WHERE b.id=? AND o.user_id=?""", (business_id, user_id)).fetchone()
        return dict(row) if row else None


def get_business_summary(user_id):
    with connect() as con:
        rows = con.execute("""SELECT b.id,b.name,b.idea,b.target_customer,b.location,b.price,
            b.variable_cost,b.revenue_model,b.initial_budget,o.assessment_json
            FROM businesses b JOIN web_business_owners o ON o.business_id=b.id
            WHERE o.user_id=? ORDER BY b.id DESC""", (user_id,)).fetchall()
        output = []
        for row in rows:
            d = dict(row)
            try:
                assessment = json.loads(d.pop("assessment_json") or "{}")
            except json.JSONDecodeError:
                assessment = {}
            ex = con.execute("SELECT id,experiment,status FROM experiments WHERE business_id=? ORDER BY id DESC LIMIT 1", (d["id"],)).fetchone()
            d["latest_experiment"] = dict(ex) if ex else None
            d["latest_decision"] = (assessment.get("decision") or {}).get("decision", "Assessment saved")
            output.append(d)
        return output


def get_business_detail(user_id, business_id):
    b = get_owned_business(user_id, business_id)
    if not b:
        return None
    try:
        assessment = json.loads(b.get("assessment_json") or "{}")
    except json.JSONDecodeError:
        assessment = {}
    with connect() as con:
        assumption_rows = con.execute("""SELECT id,statement,importance,evidence,risk,confidence
            FROM assumptions WHERE business_id=? ORDER BY id""", (business_id,)).fetchall()
        experiment_rows = con.execute("""SELECT id,assumption_id,experiment,success_metric,estimated_cost,duration,
            planned_sample_size,result,observations,sample_size,successes,status
            FROM experiments WHERE business_id=? ORDER BY id""", (business_id,)).fetchall()
        evaluations = assessment.get("assumption_evaluations", {})
        assumptions = []
        for a in assumption_rows:
            item = dict(a)
            item["evaluation"] = evaluations.get(str(item["id"]))
            assumptions.append(item)
        experiments = [dict(x) for x in experiment_rows]
    for key in ("assessment_json",):
        b.pop(key, None)
    b["decision"] = assessment.get("decision", {})
    b["assumptions"] = assumptions
    b["experiments"] = experiments
    return b


def create_business_row(user_id, business):
    # Avoid save_business()'s global duplicate scan; ownership is checked first here.
    with connect() as con:
        duplicate = con.execute("""SELECT b.id FROM businesses b JOIN web_business_owners o ON o.business_id=b.id
            WHERE o.user_id=? AND LOWER(TRIM(b.name))=LOWER(TRIM(?))
            AND LOWER(TRIM(b.idea))=LOWER(TRIM(?)) ORDER BY b.id LIMIT 1""",
            (user_id, business.name, business.idea)).fetchone()
        if duplicate:
            raise ExistingBusiness(duplicate["id"])
        cur = con.execute("""INSERT INTO businesses(name,idea,target_customer,location,price,
            revenue_model,initial_budget,variable_cost) VALUES(?,?,?,?,?,?,?,?)""",
            (business.name.strip(), business.idea.strip(), business.target_customer.strip(), business.location.strip(),
             business.price, business.revenue_model.strip(), business.initial_budget, business.variable_cost))
        business_id = cur.lastrowid
        con.execute("INSERT INTO web_business_owners(business_id,user_id,assessment_json,created_at) VALUES(?,?,?,?)",
                    (business_id, user_id, "{}", int(time.time())))
        con.commit()
    return business_id


class ExistingBusiness(Exception):
    def __init__(self, business_id):
        self.business_id = int(business_id)


def run_validation(user_id, payload):
    business = BusinessProfile.model_validate(payload)
    for field in ("name", "idea", "target_customer", "location", "revenue_model"):
        if not getattr(business, field).strip():
            raise ValueError(f"{field.replace('_', ' ').capitalize()} cannot be blank.")
    if min(business.price, business.variable_cost, business.initial_budget) < 0:
        raise ValueError("Price, costs, and budget must be zero or greater.")
    business_id = create_business_row(user_id, business)
    prompt = f"""
You are Veyntara AI, a business validation agent. Identify the 5 most important assumptions behind this business idea.
Business information:
Name: {business.name}
Idea: {business.idea}
Target customer: {business.target_customer}
Location: {business.location}
Price per unit: ₹{business.price}
Variable cost per unit: ₹{business.variable_cost}
Revenue model: {business.revenue_model}
Initial budget: ₹{business.initial_budget}

Return ONLY a JSON object: {{"assumptions":[{{"statement":"...","importance":"High","evidence":"..."}}]}}
Rules: do not invent evidence; if unavailable say "Evidence not yet available." Use search_web only when useful.
Importance must be Low, Medium, or High.
"""
    try:
        answer = ask_ai(prompt)
        if not isinstance(answer, str) or answer.strip() == "The agent reached its research limit.":
            raise RuntimeError("The AI agent did not complete its research.")
        start = answer.find("{")
        if start < 0:
            raise RuntimeError("The AI response did not contain JSON.")
        parsed, _ = json.JSONDecoder().raw_decode(answer[start:])
        assumption_list = AssumptionList.model_validate(parsed)
        evaluation_raw = evaluate_evidence([{"statement": x.statement, "evidence": x.evidence} for x in assumption_list.assumptions])
        evaluation_data = json.loads(evaluation_raw)
        evaluations = evaluation_data["evaluations"]
        if len(evaluations) != len(assumption_list.assumptions):
            raise RuntimeError("Evidence evaluation count did not match assumptions.")
        for a, ev in zip(assumption_list.assumptions, evaluations):
            a.evaluation = EvidenceEvaluation.model_validate(ev)
        decisions = evaluate_all_assumptions(assumption_list.assumptions)
        assumption_ids = []
        for assumption, dec in zip(assumption_list.assumptions, decisions):
            aid = save_assumption(business_id=business_id, assumption=assumption)
            update_assumption_evaluation(aid, risk=dec["risk"], confidence=dec["confidence"])
            assumption_ids.append(aid)
        overall = make_decision(decisions)
        exp_payload = None
        if overall.get("priority_assumptions"):
            priority = overall["priority_assumptions"][0]
            experiment = generate_experiment(priority["statement"])
            eid = save_experiment(business_id, assumption_ids[priority["original_index"]], experiment, None)
            exp_payload = json_safe(experiment)
            exp_payload.update({"id": eid, "status": "planned"})
        evaluation_map = {}
        for aid, assumption in zip(assumption_ids, assumption_list.assumptions):
            evaluation_map[str(aid)] = json_safe(assumption.evaluation)
        assessment = {"decision": json_safe(overall), "assumption_evaluations": evaluation_map}
        with connect() as con:
            con.execute("UPDATE web_business_owners SET assessment_json=? WHERE business_id=? AND user_id=?",
                        (json_dump(assessment), business_id, user_id))
            con.commit()
        return {"business_id": business_id, "decision": json_safe(overall), "experiment": exp_payload}
    except Exception as exc:
        # Keep the business but disclose that analysis failed; never silently create duplicates.
        raise RuntimeError(f"Analysis did not finish. Business ID {business_id} was saved; open it to retry or review it. Details: {type(exc).__name__}") from exc


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def log_message(self, fmt, *args):
        print("[web]", fmt % args)

    def _send_json(self, status, payload, cookie=None, clear_cookie=False):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if cookie:
            self.send_header("Set-Cookie", f"{COOKIE_NAME}={cookie}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_SECONDS}")
        elif clear_cookie:
            self.send_header("Set-Cookie", f"{COOKIE_NAME}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0")
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ValueError("Invalid request length.")
        if length < 1 or length > MAX_BODY_BYTES:
            raise ValueError("Request body is empty or too large.")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _require_user(self):
        user = get_session_user(self)
        if not user:
            self._send_json(401, {"error": "Please log in again."})
            return None
        return user

    def _origin_ok(self):
        origin = self.headers.get("Origin")
        if not origin:
            return True
        return origin in (
    f"http://127.0.0.1:{PORT}",
    f"http://localhost:{PORT}",
    f"http://172.20.10.7:{PORT}",
)


    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            return self._send_json(200, {"status":"ok","database":"separate web database","message":"Health check does not call AI or write business records."})
        if path == "/api/me":
            user = get_session_user(self)
            if not user:
                return self._send_json(401, {"error":"Not logged in."})
            return self._send_json(200, {"user":user})
        if path == "/api/businesses":
            user = self._require_user()
            if user:
                return self._send_json(200, {"businesses":get_business_summary(user["id"])})
            return
        if path.startswith("/api/businesses/"):
            user = self._require_user()
            if not user:
                return
            try:
                business_id = int(path.split("/")[3])
            except (ValueError, IndexError):
                return self._send_json(400, {"error":"Invalid business ID."})
            business = get_business_detail(user["id"], business_id)
            return self._send_json(200, {"business":business}) if business else self._send_json(404, {"error":"Business not found."})
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path not in ("/api/signup","/api/login","/api/logout") and not self._origin_ok():
            return self._send_json(403, {"error":"Request origin rejected."})
        if path in ("/api/signup","/api/login"):
            try:
                data = self._body()
                email = str(data.get("email","")).strip().lower()
                password = data.get("password","")
                if not isinstance(password,str) or len(password) < 10 or len(password) > 128:
                    return self._send_json(400, {"error":"Password must be between 10 and 128 characters."})
                if not email or len(email)>254 or "@" not in email:
                    return self._send_json(400, {"error":"Enter a valid email address."})
                with connect() as con:
                    if path == "/api/signup":
                        name = str(data.get("name","")).strip()
                        if not name or len(name)>100:
                            return self._send_json(400, {"error":"Enter a name (up to 100 characters)."})
                        salt, digest = hash_password(password)
                        try:
                            cur = con.execute("INSERT INTO web_users(name,email,password_salt,password_hash,created_at) VALUES(?,?,?,?,?)",
                                              (name,email,salt,digest,int(time.time())))
                            user_id = cur.lastrowid
                        except sqlite3.IntegrityError:
                            return self._send_json(409, {"error":"An account with this email already exists. Log in instead."})
                    else:
                        row = con.execute("SELECT * FROM web_users WHERE email=? COLLATE NOCASE",(email,)).fetchone()
                        if not row:
                            return self._send_json(401, {"error":"Email or password is incorrect."})
                        _, candidate = hash_password(password, bytes(row["password_salt"]))
                        if not hmac.compare_digest(candidate, bytes(row["password_hash"])):
                            return self._send_json(401, {"error":"Email or password is incorrect."})
                        user_id = row["id"]
                    user = con.execute("SELECT id,name,email FROM web_users WHERE id=?",(user_id,)).fetchone()
                    token = secrets.token_urlsafe(32)
                    con.execute("INSERT INTO web_sessions(token_hash,user_id,expires_at) VALUES(?,?,?)",
                                (token_digest(token),user_id,int(time.time())+SESSION_SECONDS))
                    con.commit()
                return self._send_json(200, {"user":public_user(user)}, cookie=token)
            except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
                return self._send_json(400, {"error":str(exc) if str(exc) else "Invalid request."})
        if path == "/api/logout":
            token = None
            for item in self.headers.get("Cookie","").split(";"):
                key,sep,value=item.strip().partition("=")
                if sep and key==COOKIE_NAME: token=value
            if token:
                with connect() as con:
                    con.execute("DELETE FROM web_sessions WHERE token_hash=?",(token_digest(token),));con.commit()
            return self._send_json(200, {"ok":True}, clear_cookie=True)
        user = self._require_user()
        if not user:
            return
        try:
            data = self._body()
            if path == "/api/validate":
                try:
                    result = run_validation(user["id"], data)
                    return self._send_json(200,result)
                except ExistingBusiness as exc:
                    return self._send_json(409,{"error":f"EXISTING_BUSINESS:{exc.business_id}"})
            if path.startswith("/api/businesses/") and path.endswith("/result"):
                parts=path.strip("/").split("/")
                if len(parts)!=6 or parts[3]!="experiments" or parts[5]!="result": return self._send_json(404,{"error":"Endpoint not found."})
                business_id, experiment_id=int(parts[2]),int(parts[4])
                if not get_owned_business(user["id"],business_id): return self._send_json(404,{"error":"Business not found."})
                outcome=str(data.get("result",""))
                observations=str(data.get("observations","")).strip()
                if outcome not in ("Supports","Contradicts","Unclear") or not observations:
                    return self._send_json(400,{"error":"Choose an outcome and enter observations."})
                sample=data.get("sample_size"); successes=data.get("successes")
                sample=None if sample in (None,"") else int(sample)
                successes=None if successes in (None,"") else int(successes)
                if sample is not None and sample<0 or successes is not None and successes<0:
                    return self._send_json(400,{"error":"Sample size and successes must be zero or greater."})
                if sample is not None and successes is not None and successes>sample:
                    return self._send_json(400,{"error":"Successful outcomes cannot exceed the sample size."})
                with connect() as con:
                    exp=con.execute("SELECT id FROM experiments WHERE id=? AND business_id=?",(experiment_id,business_id)).fetchone()
                    if not exp:return self._send_json(404,{"error":"Experiment not found."})
                    con.execute("UPDATE experiments SET result=?,observations=?,sample_size=?,successes=?,status='completed' WHERE id=?",
                                (outcome,observations,sample,successes,experiment_id));con.commit()
                return self._send_json(200,{"ok":True})
            if path.startswith("/api/businesses/") and path.endswith("/experiments"):
                parts=path.strip("/").split("/")
                if len(parts)!=4:return self._send_json(404,{"error":"Endpoint not found."})
                business_id=int(parts[2]);business=get_owned_business(user["id"],business_id)
                if not business:return self._send_json(404,{"error":"Business not found."})
                aid=data.get("assumption_id")
                with connect() as con:
                    a=con.execute("SELECT id,statement FROM assumptions WHERE id=? AND business_id=?",(aid,business_id)).fetchone()
                if not a:return self._send_json(400,{"error":"Choose an assumption belonging to this business."})
                experiment=Experiment(assumption=a["statement"],experiment=str(data.get("experiment","")).strip(),
                    success_metric=str(data.get("success_metric","")).strip(),estimated_cost=data.get("estimated_cost"),
                    duration=str(data.get("duration","")).strip(),planned_sample_size=data.get("planned_sample_size"))
                if not experiment.experiment or not experiment.success_metric or not experiment.duration:
                    return self._send_json(400,{"error":"Experiment, success metric, and duration are required."})
                eid=save_experiment(business_id,aid,experiment,None)
                return self._send_json(200,{"ok":True,"experiment_id":eid})
            return self._send_json(404, {"error":"Endpoint not found."})
        except ValidationError as exc:
            return self._send_json(422,{"error":"Please check the submitted fields.","details":[{"field":".".join(map(str,x["loc"])),"message":x["msg"]} for x in exc.errors()]})
        except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            return self._send_json(400,{"error":str(exc) or "Invalid request."})
        except Exception as exc:
            print(f"[api] Request failed: {type(exc).__name__}: {exc}")
            return self._send_json(500,{"error":"The request could not be completed. Check the PowerShell server log before retrying."})


if __name__ == "__main__":
    if not FRONTEND_DIR.is_dir() or not (FRONTEND_DIR / "index.html").is_file():
        raise SystemExit("Frontend files are missing. Expected frontend beside web_app.py.")
    init_web_database()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Local access: http://127.0.0.1:{PORT}")
    print(f"Hotspot access: http://172.20.10.7:{PORT}")
    print(f"Web database: {WEB_DB_PATH}")
    print("The existing veyntara.db is not used by this web adapter.")
    print("Local-only development server. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Veyntara AI web adapter.")
    finally:
        server.server_close()
