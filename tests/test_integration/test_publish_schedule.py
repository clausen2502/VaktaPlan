# tests/test_integration/test_flow_publish_schedule.py
import unittest
from types import SimpleNamespace as Obj

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from core.database import Base, get_db


class IntegrationFlowTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
        Base.metadata.create_all(self.engine)
        TestingSession = sessionmaker(bind=self.engine, future=True)
        self.SessionLocal = TestingSession

        # --- Dependency overrides ---
        def _get_db_override():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = _get_db_override

        # Pretend current user is a manager in org_id=1 with id=10
        app.dependency_overrides[
            # auth.services.auth_service.get_current_active_user
            __import__("auth").services.auth_service.get_current_active_user
        ] = lambda: Obj(id=10, org_id=1)

        # Bypass manager check
        app.dependency_overrides[
            # authz.deps.require_manager
            __import__("authz").deps.require_manager
        ] = lambda: None

        self.client = TestClient(app)

        # --- Seed an Organization with id=1 directly (so user.org_id aligns) ---
        # Using API to create the org is possible, but it returns an ID we’d
        # then have to wire back into the user override. Seeding is simpler.
        with self.SessionLocal() as db:
            db.execute(
                # minimal insert: name + timezone
                # Works in SQLite; in Postgres you'd use proper ORM add/commit.
                # Here we want a quick, explicit insert that keeps id=1.
                # But safer cross-DB is ORM:
                __import__("sqlalchemy").text(
                    "INSERT INTO organizations (name, timezone) VALUES (:n, :tz)"
                ),
                {"n": "Org One", "tz": "Atlantic/Reykjavik"},
            )
            db.commit()

    def tearDown(self):
        # Clear dependency overrides
        for dep in [get_db,
                    __import__("auth").services.auth_service.get_current_active_user,
                    __import__("authz").deps.require_manager]:
            app.dependency_overrides.pop(dep, None)
        self.engine.dispose()

    def test_full_publish_flow(self):
        json = "Content-Type: application/json"
        auth = lambda: "Authorization: Bearer dummy"

        # 1) Create a location
        r = self.client.post(
            "/api/locations",
            headers={"Content-Type": "application/json"},
            json={"name": "HQ"},
        )
        self.assertEqual(r.status_code, 201, r.text)
        loc_id = r.json()["id"]

        # 2) Create a job role
        r = self.client.post(
            "/api/jobroles",
            headers={"Content-Type": "application/json"},
            json={"name": "Cashier"},
        )
        self.assertEqual(r.status_code, 201, r.text)
        role_id = r.json()["id"]

        # 3) Create an employee
        r = self.client.post(
            "/api/employees",
            headers={"Content-Type": "application/json"},
            json={"display_name": "Jonas"},
        )
        self.assertEqual(r.status_code, 201, r.text)
        emp_id = r.json()["id"]

        # 4) Create a draft shift (TZ-aware times)
        r = self.client.post(
            "/api/shifts",
            headers={"Content-Type": "application/json"},
            json={
                "location_id": loc_id,
                "role_id": role_id,
                "start_at": "2025-10-01T09:00:00Z",
                "end_at": "2025-10-01T17:00:00Z",
                "status": "draft",
                "notes": "Front desk",
            },
        )
        self.assertEqual(r.status_code, 201, r.text)
        shift_id = r.json()["id"]

        # 5) Assign the employee to the shift
        r = self.client.post(
            "/api/assignments",
            headers={"Content-Type": "application/json"},
            json={"shift_id": shift_id, "employee_id": emp_id, "preference_score": 4},
        )
        self.assertIn(r.status_code, (200, 201), r.text)
        self.assertEqual(r.json()["shift_id"], shift_id)
        self.assertEqual(r.json()["employee_id"], emp_id)

        # 6) Publish the week covering that shift
        r = self.client.post(
            "/api/publications",
            headers={"Content-Type": "application/json"},
            json={"range_start": "2025-10-01", "range_end": "2025-10-07"},
        )
        self.assertEqual(r.status_code, 201, r.text)
        pub = r.json()
        self.assertEqual(pub["range_start"], "2025-10-01")
        self.assertEqual(pub["range_end"], "2025-10-07")
        self.assertEqual(pub["version"], 1)

        # 7a) Verify publications list filters by active_on
        r = self.client.get("/api/publications?active_on=2025-10-03")
        self.assertEqual(r.status_code, 200, r.text)
        pubs = r.json()
        self.assertEqual(len(pubs), 1)
        self.assertEqual(pubs[0]["range_start"], "2025-10-01")

        # 7b) Verify assignments list for that shift
        r = self.client.get(f"/api/assignments?shift_id={shift_id}")
        self.assertEqual(r.status_code, 200, r.text)
        assigns = r.json()
        self.assertEqual(len(assigns), 1)
        self.assertEqual(assigns[0]["shift_id"], shift_id)
        self.assertEqual(assigns[0]["employee_id"], emp_id)


if __name__ == "__main__":
    unittest.main()
