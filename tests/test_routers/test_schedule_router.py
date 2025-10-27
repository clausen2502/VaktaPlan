# tests/test_routers/test_schedule_router.py
import unittest
from types import SimpleNamespace as Obj
from datetime import date
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from main import app
from core.database import get_db
from auth.services.auth_service import get_current_active_user
from authz.deps import require_manager


class ScheduleRouterTests(unittest.TestCase):
    def setUp(self):
        # Minimal fake DB (router never touches DB directly in these tests)
        class FakeDB:
            def rollback(self): ...
        def _fake_db():
            yield FakeDB()

        app.dependency_overrides[get_db] = _fake_db

        # Fake logged-in manager scoped to org 1
        app.dependency_overrides[get_current_active_user] = lambda: Obj(
            org_id=1, id=123, is_manager=True   # <-- add is_manager for safety
        )
        # Bypass manager check entirely (POST/DELETE)
        app.dependency_overrides[require_manager] = lambda: None  # <-- no-op

        self.client = TestClient(app)

    def tearDown(self):
        for dep in (get_db, get_current_active_user, require_manager):
            app.dependency_overrides.pop(dep, None)

    # ---------- LIST ----------
    @patch("schedule.router.service.get_schedules")
    def test_list_schedules_passes_filters_and_org(self, mock_get):
        mock_get.return_value = [
            Obj(
                id=1, org_id=1, range_start=date(2025,10,1), range_end=date(2025,10,31),
                version=1, status="draft", created_by=123, published_at=None
            )
        ]
        r = self.client.get("/api/schedules?active_on=2025-10-15&start_from=2025-10-01&end_to=2025-12-31")
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual(body[0]["id"], 1)
        # verify router forwarded filters + org_id
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs["org_id"], 1)
        self.assertEqual(str(kwargs["active_on"]), "2025-10-15")
        self.assertEqual(str(kwargs["start_from"]), "2025-10-01")
        self.assertEqual(str(kwargs["end_to"]), "2025-12-31")

    # ---------- GET BY ID ----------
    @patch("schedule.router.service.get_schedule_for_org")
    def test_get_schedule_ok(self, mock_get_one):
        mock_get_one.return_value = Obj(
            id=9, org_id=1, range_start=date(2025,11,1), range_end=date(2025,11,30),
            version=2, status="draft", created_by=123, published_at=None
        )
        r = self.client.get("/api/schedules/9")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["id"], 9)

    @patch("schedule.router.service.get_schedule_for_org")
    def test_get_schedule_404(self, mock_get_one):
        mock_get_one.return_value = None
        r = self.client.get("/api/schedules/9999")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json()["detail"], "schedule not found")

    # ---------- CREATE ----------
    @patch("schedule.router.service.create_schedule")
    def test_create_schedule_201(self, mock_create):
        mock_create.return_value = Obj(
            id=3, org_id=1, range_start=date(2025,12,1), range_end=date(2025,12,31),
            version=1, status="draft", created_by=123, published_at=None
        )
        payload = {"range_start": "2025-12-01", "range_end": "2025-12-31", "version": 1}
        r = self.client.post("/api/schedules", json=payload)
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(r.json()["id"], 3)

    @patch("schedule.router.service.create_schedule")
    def test_create_schedule_409_conflict(self, mock_create):
        # router maps IntegrityError to 409
        mock_create.side_effect = IntegrityError(None, None, None)
        payload = {"range_start": "2025-12-01", "range_end": "2025-12-31", "version": 1}
        r = self.client.post("/api/schedules", json=payload)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()["detail"], "schedule already exists for this range and version")

    # ---------- DELETE ----------
    @patch("schedule.router.service.delete_schedule")
    @patch("schedule.router.service.get_schedule_for_org")
    def test_delete_schedule_200(self, mock_get_one, mock_delete):
        mock_get_one.return_value = Obj(id=5, org_id=1)
        mock_delete.return_value = None
        r = self.client.delete("/api/schedules/5")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"message": "schedule deleted"})

    @patch("schedule.router.service.get_schedule_for_org")
    def test_delete_schedule_404(self, mock_get_one):
        mock_get_one.return_value = None
        r = self.client.delete("/api/schedules/404404")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json()["detail"], "schedule not found")


if __name__ == "__main__":
    unittest.main()
