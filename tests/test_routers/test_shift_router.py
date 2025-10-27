import unittest
from types import SimpleNamespace as Obj
from unittest.mock import patch
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from fastapi import HTTPException

from main import app
from core.database import get_db
from auth.services.auth_service import get_current_active_user


class ShiftRouterTests(unittest.TestCase):
    def setUp(self):
        # Minimal fake DB (router doesn't hit DB directly in these tests)
        class FakeDB:
            def rollback(self): ...
        def _fake_db():
            yield FakeDB()

        app.dependency_overrides[get_db] = _fake_db
        # fake logged-in user scoped to org 1
        app.dependency_overrides[get_current_active_user] = lambda: Obj(org_id=1, id=123)

        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_active_user, None)

    # ---------- LIST ----------
    @patch("shift.router.service.get_shifts")
    def test_get_shifts_returns_dummy_and_forces_org(self, mock_get_shifts):
        mock_get_shifts.return_value = [
            Obj(
                id=1,
                org_id=1,
                schedule_id=10,
                location_id=1,
                role_id=1,
                start_at=datetime(2025, 10, 16, 9, 0, tzinfo=timezone.utc),
                end_at=datetime(2025, 10, 16, 17, 0, tzinfo=timezone.utc),
                notes="hello",
            )
        ]

        resp = self.client.get("/api/shifts/")
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertEqual(data[0]["id"], 1)
        self.assertEqual(data[0]["org_id"], 1)
        self.assertEqual(data[0]["schedule_id"], 10)

        # verify router passed org_id=1 to service
        _, kwargs = mock_get_shifts.call_args
        self.assertEqual(kwargs.get("org_id"), 1)

    @patch("shift.router.service.get_shifts")
    def test_get_shifts_can_filter_by_schedule_id(self, mock_get_shifts):
        mock_get_shifts.return_value = []
        resp = self.client.get("/api/shifts?schedule_id=10")
        self.assertEqual(resp.status_code, 200, resp.text)
        _, kwargs = mock_get_shifts.call_args
        self.assertEqual(kwargs.get("schedule_id"), 10)

    # ---------- CREATE ----------
    @patch("shift.router.service.create_shift")
    def test_post_creates_shift(self, mock_create_shift):
        mock_create_shift.return_value = Obj(
            id=2,
            org_id=1,
            schedule_id=10,
            location_id=1,
            role_id=1,
            start_at=datetime(2025, 10, 17, 9, 0, tzinfo=timezone.utc),
            end_at=datetime(2025, 10, 17, 17, 0, tzinfo=timezone.utc),
            notes="created via test",
        )

        payload = {
            "schedule_id": 10,
            "location_id": 1,
            "role_id": 1,
            "start_at": "2025-10-17T09:00:00Z",
            "end_at":   "2025-10-17T17:00:00Z",
            "notes": "created via test"
        }
        resp = self.client.post("/api/shifts", json=payload)
        self.assertEqual(resp.status_code, 201, resp.text)
        self.assertEqual(resp.json()["id"], 2)

    @patch("shift.router.service.create_shift")
    def test_post_422_when_client_sends_org_id(self, _mock_create_shift):
        # org_id is forbidden in payload (router injects from auth)
        payload = {
            "org_id": 2,
            "schedule_id": 10,
            "location_id": 1,
            "role_id": 1,
            "start_at": "2025-10-17T09:00:00Z",
            "end_at":   "2025-10-17T17:00:00Z",
        }
        resp = self.client.post("/api/shifts", json=payload)
        self.assertEqual(resp.status_code, 422)

    @patch("shift.router.service.create_shift")
    def test_post_422_on_end_before_start(self, mock_create_shift):
        # service raises; router should pass it through
        mock_create_shift.side_effect = HTTPException(status_code=422, detail="start_at must be before end_at")
        payload = {
            "schedule_id": 10,
            "location_id": 1,
            "role_id": 1,
            "start_at": "2025-10-17T10:00:00Z",
            "end_at":   "2025-10-17T09:00:00Z",
        }
        resp = self.client.post("/api/shifts", json=payload)
        self.assertEqual(resp.status_code, 422)

    # ---------- GET BY ID ----------
    @patch("shift.router.service.get_shift_for_org")
    def test_get_shift(self, mock_get_for_org):
        mock_get_for_org.return_value = Obj(
            id=1,
            org_id=1,
            schedule_id=10,
            location_id=1,
            role_id=1,
            start_at=datetime(2025, 10, 17, 9, 0, tzinfo=timezone.utc),
            end_at=datetime(2025, 10, 17, 17, 0, tzinfo=timezone.utc),
            notes="created via test",
        )
        resp = self.client.get("/api/shifts/1")
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertEqual(data["id"], 1)
        self.assertEqual(data["org_id"], 1)
        self.assertEqual(data["schedule_id"], 10)

    @patch("shift.router.service.get_shift_for_org")
    def test_get_shift_404_cross_org_hidden(self, mock_get_for_org):
        mock_get_for_org.return_value = None
        resp = self.client.get("/api/shifts/9999")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "Shift not found")

    # ---------- DELETE ----------
    @patch("shift.router.service.delete_shift")
    @patch("shift.router.service.get_shift_for_org")
    def test_delete_200(self, mock_get_for_org, mock_delete):
        mock_get_for_org.return_value = Obj(id=2, org_id=1)
        mock_delete.return_value = None
        resp = self.client.delete("/api/shifts/2")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"message": "Shift deleted"})

    @patch("shift.router.service.get_shift_for_org")
    def test_delete_404(self, mock_get_for_org):
        mock_get_for_org.return_value = None
        resp = self.client.delete("/api/shifts/999999")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "Shift not found")

    # ---------- PATCH ----------
    @patch("shift.router.service.update_shift")
    @patch("shift.router.service.get_shift_for_org")
    def test_patch_shift_200(self, mock_get_for_org, mock_update):
        mock_get_for_org.return_value = Obj(
            id=1, org_id=1, schedule_id=10, location_id=1, role_id=1,
            start_at=datetime(2025, 10, 16, 9, 0, tzinfo=timezone.utc),
            end_at=datetime(2025, 10, 16, 17, 0, tzinfo=timezone.utc),
            notes="front desk"
        )
        mock_update.return_value = Obj(
            id=1, org_id=1, schedule_id=10, location_id=1, role_id=1,
            start_at=datetime(2025, 10, 16, 9, 0, tzinfo=timezone.utc),
            end_at=datetime(2025, 10, 16, 18, 0, tzinfo=timezone.utc),
            notes="front desk"
        )

        resp = self.client.patch("/api/shifts/1", json={"end_at": "2025-10-16T18:00:00Z"})
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertEqual(data["id"], 1)
        self.assertEqual(data["end_at"], "2025-10-16T18:00:00Z")

    @patch("shift.router.service.get_shift_for_org")
    def test_patch_shift_404(self, mock_get_for_org):
        mock_get_for_org.return_value = None
        resp = self.client.patch("/api/shifts/9999", json={"end_at": "2025-10-16T18:00:00Z"})
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "Shift not found")

    @patch("shift.router.service.get_shift_for_org")
    @patch("shift.router.service.update_shift")
    def test_patch_shift_422(self, mock_update, mock_get_for_org):
        mock_get_for_org.return_value = Obj(id=1, org_id=1)
        mock_update.side_effect = HTTPException(status_code=422, detail="start_at must be before end_at")

        payload = {
            "start_at": "2025-10-16T19:00:00Z",
            "end_at":   "2025-10-16T18:00:00Z",
        }
        resp = self.client.patch("/api/shifts/1", json=payload)
        self.assertEqual(resp.status_code, 422)


if __name__ == "__main__":
    unittest.main()
