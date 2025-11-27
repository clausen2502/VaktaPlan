# tests/test_routers/test_autoassignservice_router.py

import unittest
from types import SimpleNamespace as Obj
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from core.database import get_db
from auth.services.auth_service import get_current_active_user
from authz.deps import require_manager


class AutoAssignRouterTests(unittest.TestCase):
    def setUp(self):
        class FakeDB:
            def __init__(self):
                # we'll set this per-test when needed
                self._schedule = None

            def rollback(self):
                pass

            def get(self, model, pk):
                # router only uses this for Schedule lookup
                return self._schedule

        self.fake_db = FakeDB()

        def _fake_db():
            yield self.fake_db

        app.dependency_overrides[get_db] = _fake_db
        app.dependency_overrides[get_current_active_user] = (
            lambda: Obj(org_id=1, id=123)
        )
        app.dependency_overrides[require_manager] = lambda: None

        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_active_user, None)
        app.dependency_overrides.pop(require_manager, None)

    # --- POST /api/assignments/auto-assign ---

    @patch("assignment.router.auto_assign_service")
    def test_auto_assign_happy_path(self, mock_auto_assign):
        # schedule belongs to the same org as the user (org_id = 1)
        self.fake_db._schedule = Obj(id=42, org_id=1)

        mock_auto_assign.return_value = {
            "assigned": 5,
            "skipped_full": 2,
            "skipped_no_candidates": 1,
            "policy": "fill_missing",
        }

        resp = self.client.post(
            "/api/assignments/auto-assign",
            json={
                "schedule_id": 42,
                "start_date": "2025-01-01",
                "end_date": "2025-01-07",
                "policy": "fill_missing",
                "dry_run": False,
            },
        )

        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertEqual(data["assigned"], 5)
        self.assertEqual(data["skipped_full"], 2)
        self.assertEqual(data["skipped_no_candidates"], 1)
        self.assertEqual(data["policy"], "fill_missing")

        # ensure service was called correctly
        mock_auto_assign.assert_called_once()
        _, kwargs = mock_auto_assign.call_args
        self.assertEqual(kwargs["schedule_id"], 42)
        self.assertEqual(str(kwargs["start_date"]), "2025-01-01")
        self.assertEqual(str(kwargs["end_date"]), "2025-01-07")
        self.assertEqual(kwargs["policy"], "fill_missing")
        self.assertFalse(kwargs["dry_run"])

    @patch("assignment.router.auto_assign_service")
    def test_auto_assign_404_schedule_not_found(self, mock_auto_assign):
        # no schedule in DB
        self.fake_db._schedule = None

        resp = self.client.post(
            "/api/assignments/auto-assign",
            json={
                "schedule_id": 999,
                "start_date": "2025-01-01",
                "end_date": "2025-01-07",
                "policy": "fill_missing",
                "dry_run": False,
            },
        )

        self.assertEqual(resp.status_code, 404, resp.text)
        self.assertEqual(resp.json()["detail"], "schedule not found")
        mock_auto_assign.assert_not_called()

    @patch("assignment.router.auto_assign_service")
    def test_auto_assign_404_schedule_wrong_org(self, mock_auto_assign):
        # user org_id = 1, schedule belongs to org_id = 2
        self.fake_db._schedule = Obj(id=42, org_id=2)

        resp = self.client.post(
            "/api/assignments/auto-assign",
            json={
                "schedule_id": 42,
                "start_date": "2025-01-01",
                "end_date": "2025-01-07",
                "policy": "fill_missing",
                "dry_run": False,
            },
        )

        self.assertEqual(resp.status_code, 404, resp.text)
        self.assertEqual(resp.json()["detail"], "schedule not found")
        mock_auto_assign.assert_not_called()
