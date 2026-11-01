import os
import tempfile
import unittest
from pathlib import Path
import sqlite3
from contextlib import contextmanager
from fastapi.testclient import TestClient

import fastapi_app


core = fastapi_app.core
ORIGIN = "http://127.0.0.1:5500"


class FastAPITestCase(unittest.TestCase):
    @classmethod
    @contextmanager
    def isolated_connect(cls):
        conn = sqlite3.connect(str(cls.test_db), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()
    @classmethod
    def setUpClass(cls):
        # Create an isolated database for all API tests.
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.test_db = Path(cls.temp_dir.name) / "fastapi_test.db"

        cls.original_web_db = core.WEB_DB_PATH
        cls.original_db_name = core.database.DB_NAME

        core.WEB_DB_PATH = cls.test_db
        core.database.DB_NAME = str(cls.test_db)
        cls.original_connect = core.connect
        core.connect = cls.isolated_connect
    @classmethod
    def tearDownClass(cls):
        # Restore original database configuration.
        core.WEB_DB_PATH = cls.original_web_db
        core.database.DB_NAME = cls.original_db_name
        core.connect = cls.original_connect
        cls.temp_dir.cleanup()

    def setUp(self):
        self.client = TestClient(fastapi_app.app)
        self.client.__enter__()

        self.reset_database()

        # Create two independent authenticated users.
        self.user_a = self.signup(
            "Test User A", "usera@example.com"
        )
        self.user_b = self.signup(
            "Test User B", "userb@example.com"
        )
        self.client.post(
            "/api/login",
            headers={"Origin": ORIGIN},
            json={
                "email": "usera@example.com",
                "password": "TestPassword123!"
            }
        )

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def reset_database(self):
        with core.connect() as con:
            con.execute("DELETE FROM web_sessions")
            con.execute("DELETE FROM web_business_owners")
            con.execute("DELETE FROM experiments")
            con.execute("DELETE FROM assumptions")
            con.execute("DELETE FROM web_users")
            con.execute("DELETE FROM businesses")
            con.commit()

    def signup(self, name, email):
        response = self.client.post(
            "/api/signup",
            headers={"Origin": ORIGIN},
            json={
                "name": name,
                "email": email,
                "password": "TestPassword123!"
            }
        )

        self.assertEqual(response.status_code, 200)
        return response.json()["user"]

    def seed_business(self, user_id):
        with core.connect() as con:
            cursor = con.execute(
                """
                INSERT INTO businesses (
                    name, idea, target_customer, location,
                    price, revenue_model, initial_budget,
                    variable_cost
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "Test Business",
                    "A business created for API testing",
                    "Test customers",
                    "Kochi",
                    100.0,
                    "Direct sales",
                    10000.0,
                    40.0
                )
            )

            business_id = cursor.lastrowid

            con.execute(
                """
                INSERT INTO web_business_owners (
                    business_id, user_id, assessment_json,
                    created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (business_id, user_id, "{}", 1000000000)
            )

            cursor = con.execute(
                """
                INSERT INTO assumptions (
                    business_id, statement, importance,
                    evidence, risk, confidence
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    business_id,
                    "Customers will pay for this product",
                    "High",
                    "Test evidence",
                    "Medium",
                    "Medium"
                )
            )

            assumption_id = cursor.lastrowid
            con.commit()

        return business_id, assumption_id

    def test_health_endpoint(self):
        response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_authentication_required(self):
        self.client.cookies.clear()

        self.assertEqual(
            self.client.get("/api/me").status_code, 401
        )
        self.assertEqual(
            self.client.get("/api/businesses").status_code, 401
        )

    def test_signup_duplicate_and_login_logout(self):
        duplicate = self.client.post(
            "/api/signup",
            headers={"Origin": ORIGIN},
            json={
                "name": "Duplicate User",
                "email": "usera@example.com",
                "password": "TestPassword123!"
            }
        )
        self.assertEqual(duplicate.status_code, 409)

        self.client.post(
            "/api/logout",
            headers={"Origin": ORIGIN}
        )

        self.assertEqual(
            self.client.get("/api/me").status_code, 401
        )

        login = self.client.post(
            "/api/login",
            headers={"Origin": ORIGIN},
            json={
                "email": "usera@example.com",
                "password": "TestPassword123!"
            }
        )

        self.assertEqual(login.status_code, 200)
        self.assertEqual(
            self.client.get("/api/me").status_code, 200
        )

    def test_invalid_signup_payload(self):
        response = self.client.post(
            "/api/signup",
            headers={"Origin": ORIGIN},
            json={
                "name": "Invalid User",
                "email": "invalid@example.com",
                "password": "short"
            }
        )

        self.assertEqual(response.status_code, 422)

    def test_untrusted_origin_rejected(self):
        response = self.client.post(
            "/api/signup",
            headers={"Origin": "https://untrusted.example"},
            json={
                "name": "Blocked User",
                "email": "blocked@example.com",
                "password": "TestPassword123!"
            }
        )

        self.assertEqual(response.status_code, 403)


    def test_business_ownership_isolation(self):
        business_id, _ = self.seed_business(
            self.user_a["id"]
        )

        # Log in as User A, the business owner.
        self.client.post(
            "/api/logout",
            headers={"Origin": ORIGIN}
        )
        self.client.post(
            "/api/login",
            headers={"Origin": ORIGIN},
            json={
                "email": "usera@example.com",
                "password": "TestPassword123!"
            }
        )

        owner_response = self.client.get(
            f"/api/businesses/{business_id}"
        )
        self.assertEqual(owner_response.status_code, 200)

        # Log in as User B, who does not own the business.
        self.client.post(
            "/api/logout",
            headers={"Origin": ORIGIN}
        )
        self.client.post(
            "/api/login",
            headers={"Origin": ORIGIN},
            json={
                "email": "userb@example.com",
                "password": "TestPassword123!"
            }
        )

        response = self.client.get(
            f"/api/businesses/{business_id}"
        )

        self.assertEqual(response.status_code, 404)

    def test_experiment_creation_and_result_validation(self):
        business_id, assumption_id = self.seed_business(
            self.user_a["id"]
        )

        create_response = self.client.post(
            f"/api/businesses/{business_id}/experiments",
            headers={"Origin": ORIGIN},
            json={
                "assumption_id": assumption_id,
                "experiment": "Interview 20 potential customers",
                "success_metric": "At least 10 interested customers",
                "estimated_cost": 500,
                "duration": "7 days",
                "planned_sample_size": 20
            }
        )

        self.assertEqual(create_response.status_code, 200)

        experiment_id = create_response.json()["experiment_id"]

        # Successful outcomes cannot exceed sample size.
        invalid_result = self.client.post(
            f"/api/businesses/{business_id}/experiments/{experiment_id}/result",
            headers={"Origin": ORIGIN},
            json={
                "result": "Supports",
                "observations": "Test observations",
                "sample_size": 5,
                "successes": 6
            }
        )

        self.assertEqual(invalid_result.status_code, 400)

        # A valid result should be saved.
        valid_result = self.client.post(
            f"/api/businesses/{business_id}/experiments/{experiment_id}/result",
            headers={"Origin": ORIGIN},
            json={
                "result": "Supports",
                "observations": "Customers showed interest",
                "sample_size": 20,
                "successes": 12
            }
        )

        self.assertEqual(valid_result.status_code, 200)

        with core.connect() as con:
            row = con.execute(
                """
                SELECT result, status, sample_size, successes
                FROM experiments WHERE id=?
                """,
                (experiment_id,)
            ).fetchone()

        self.assertEqual(row["result"], "Supports")
        self.assertEqual(row["status"], "completed")
        self.assertEqual(row["sample_size"], 20)
        self.assertEqual(row["successes"], 12)

    def test_oversized_request_rejected(self):
        response = self.client.post(
            "/api/login",
            headers={"Origin": ORIGIN},
            content=b"x" * 33000
        )

        self.assertEqual(response.status_code, 413)


if __name__ == "__main__":
    unittest.main(verbosity=2)
