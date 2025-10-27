import unittest
from types import SimpleNamespace as Obj

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
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
            __import__("auth").services.auth_service.get_current_active_user
        ] = lambda: Obj(id=10, org_id=1)

        # Bypass manager check
        app.dependency_overrides[
            __import__("authz").deps.require_manager
        ] = lambda: None

        self.client = TestClient(app)

        # --- Seed Organization id=1 ---
        with self.SessionLocal() as db:
            db.execute(
                text("INSERT INTO organizations (name, timezone) VALUES (:n, :tz)"),
                {"n": "Org One", "tz": "Atlantic/Reykjavik"},
            )
            db.commit()

    def tearDown(self):
        for dep in [get_db,
                    __import__("auth").services.auth_service.get_current_active_user,
                    __import__("authz").deps.require_manager]:
            app.dependency_overrides.pop(dep, None)
        self.engine.dispose()

    def test_full_publish_flow(self):
        # 1) Create a location
        r = self.client.post("/api/locations", json={"name": "HQ"})
        self.assertEqual(r.status_code, 201, r.text)
        loc_id = r.json()["id"]

        # 2) Create a job role
        r = self.client.post("/api/jobroles", json={"name": "Cashier"})
        self.assertEqual(r.status_code, 201, r.text)
        role_id = r.json()["id"]

        # 3) Create an employee
        r = self.client.post("/api/employees", json={"display_name": "Jonas"})
        self.assertEqual(r.status_code, 201, r.text)
        emp_id = r.json()["id"]

        # 4) Create a schedule (draft)
        r = self.client.post(
            "/api/schedules",
            json={"range_start": "2025-10-01", "range_end": "2025-10-07"}
        )
        self.assertEqual(r.status_code, 201, r.text)
        schedule = r.json()
        schedule_id = schedule["id"]

        # 5) Create a shift inside that schedule (TZ-aware times)
        r = self.client.post(
            "/api/shifts",
            json={
                "schedule_id": schedule_id,      # REQUIRED now
                "location_id": loc_id,
                "role_id": role_id,
                "start_at": "2025-10-01T09:00:00Z",
                "end_at":   "2025-10-01T17:00:00Z",
                # "status": "draft",            # ❌ removed: shift has no status
                "notes": "Front desk",
            },
        )
        self.assertEqual(r.status_code, 201, r.text)
        shift_id = r.json()["id"]

        # 6) Assign the employee to the shift
        r = self.client.post(
            "/api/assignments",
            json={"shift_id": shift_id, "employee_id": emp_id, "preference_score": 4},
        )
        self.assertIn(r.status_code, (200, 201), r.text)
        self.assertEqual(r.json()["shift_id"], shift_id)
        self.assertEqual(r.json()["employee_id"], emp_id)

        # 7) Verify schedules list filters by active_on
        r = self.client.get("/api/schedules?active_on=2025-10-03")
        self.assertEqual(r.status_code, 200, r.text)
        schedules = r.json()
        self.assertEqual(len(schedules), 1)
        self.assertEqual(schedules[0]["range_start"], "2025-10-01")
        self.assertEqual(schedules[0]["range_end"], "2025-10-07")
        self.assertEqual(schedules[0]["version"], 1)

        # 8) Verify assignments list for that shift
        r = self.client.get(f"/api/assignments?shift_id={shift_id}")
        self.assertEqual(r.status_code, 200, r.text)
        assigns = r.json()
        self.assertEqual(len(assigns), 1)
        self.assertEqual(assigns[0]["shift_id"], shift_id)
        self.assertEqual(assigns[0]["employee_id"], emp_id)


if __name__ == "__main__":
    unittest.main()
