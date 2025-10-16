import unittest
from types import SimpleNamespace as Obj
from unittest.mock import patch
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from main import app
from core.database import get_db
from shift.models import ShiftStatus

class ShiftRouterTests(unittest.TestCase):
    def setUp(self):
        # override DB dependency (won't be used because we patch service)
        def _fake_db():
            yield Obj()
        app.dependency_overrides[get_db] = _fake_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.pop(get_db, None)

    @patch("shift.router.list_shifts")
    def test_get_shifts_returns_dummy(self, mock_list_shifts):
        mock_list_shifts.return_value = [
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

    @patch("shift.router.create_shift")
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
