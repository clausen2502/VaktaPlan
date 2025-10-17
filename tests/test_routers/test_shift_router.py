import unittest
from types import SimpleNamespace as Obj
from unittest.mock import patch
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from fastapi import HTTPException

from main import app
from core.database import get_db
from shift.models import ShiftStatus

class ShiftRouterTests(unittest.TestCase):
    def setUp(self):
        # override DB dependency
        def _fake_db():
            yield Obj()
        app.dependency_overrides[get_db] = _fake_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.pop(get_db, None)

    @patch("shift.router.service.get_shifts")
    def test_get_shifts_returns_dummy(self, mock_get_shifts):
        mock_get_shifts.return_value = [
            Obj(
                id=1,
                org_id=1,
                location_id=1,
                role_id=1,
                start_at=datetime(2025, 10, 16, 9, 0, tzinfo=timezone.utc),
                end_at=datetime(2025, 10, 16, 17, 0, tzinfo=timezone.utc),
                status=ShiftStatus.draft,
                notes="hello",
            )
        ]

        resp = self.client.get("/api/shifts/")
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertEqual(data[0]["id"], 1)
        self.assertEqual(data[0]["org_id"], 1)
        self.assertEqual(data[0]["status"], "draft")

    @patch("shift.router.service.create_shift")
    def test_post_creates_shift(self, mock_create_shift):
        mock_create_shift.return_value = Obj(
            id=2,
            org_id=1,
            location_id=1,
            role_id=1,
            start_at=datetime(2025, 10, 17, 9, 0, tzinfo=timezone.utc),
            end_at=datetime(2025, 10, 17, 17, 0, tzinfo=timezone.utc),
            status=ShiftStatus.published,
            notes="created via test",
        )

        payload = {
            "org_id": 1,
            "location_id": 1,
            "role_id": 1,
            "start_at": "2025-10-17T09:00:00Z",
            "end_at":   "2025-10-17T17:00:00Z",
            "status": "published",
            "notes": "created via test"
        }
        resp = self.client.post("/api/shifts", json=payload)
        self.assertEqual(resp.status_code, 201, resp.text)
        self.assertEqual(resp.json()["id"], 2)

    @patch("shift.router.service.create_shift")
    def test_post_422_on_end_before_start(self, _mock_create_shift):
        payload = {
            "org_id": 1,
            "start_at": "2025-10-17T10:00:00Z",
            "end_at":   "2025-10-17T09:00:00Z",
            "status": "draft"
        }
        resp = self.client.post("/api/shifts", json=payload)
        self.assertEqual(resp.status_code, 422)
    
    @patch("shift.router.service.get_shift")
    @patch("shift.router.service.delete_shift")
    def test_delete_200(self, mock_delete, mock_get):
        # get_shift must return something truthy to proceed
        mock_get.return_value = Obj(id=2)
        mock_delete.return_value = None

        resp = self.client.delete("/api/shifts/2")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"message": "Shift Deleted"})

    @patch("shift.router.service.get_shift")
    def test_delete_404(self, mock_get):
        mock_get.return_value = None
        resp = self.client.delete("/api/shifts/999999")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "Shift not found")

    @patch("shift.router.service.get_shift")
    def test_get_shift(self, mock_get):
        mock_get.return_value = Obj(
        id=1,
        org_id=1,
        location_id=1,
        role_id=1,
        start_at=datetime(2025, 10, 17, 9, 0, tzinfo=timezone.utc),
        end_at=datetime(2025, 10, 17, 17, 0, tzinfo=timezone.utc),
        status=ShiftStatus.published,
        notes="created via test",
        )
        resp = self.client.get("/api/shifts/1")
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertEqual(data["id"], 1)
        self.assertEqual(data["org_id"], 1)
        self.assertEqual(data["status"], "published")
