from __future__ import annotations
import unittest
from types import SimpleNamespace as Obj
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from main import app
from core.database import get_db
from auth.services.auth_service import get_current_active_user
from authz.deps import require_manager


class WeeklyTemplateRouterTests(unittest.TestCase):
    def setUp(self):
        # Fake DB dep (we don't hit real DB in these router tests)
        class FakeDB:
            def rollback(self): pass
            def commit(self): pass
        def _fake_db():
            yield FakeDB()

        app.dependency_overrides[get_db] = _fake_db
        app.dependency_overrides[get_current_active_user] = lambda: Obj(org_id=1, id=123)
        app.dependency_overrides[require_manager] = lambda: None

        self.client = TestClient(app)
        self.base = "/api/schedules"   # assuming you mount routers under /api

    def tearDown(self):
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_active_user, None)
        app.dependency_overrides.pop(require_manager, None)

    # ---------------- LIST ----------------

    @patch("weeklytemplate.router.get_schedule_for_org")
    @patch("weeklytemplate.router.service.get_weekly_template_rows")
    def test_list_weekly_template_200(self, mock_list, mock_sched):
        mock_sched.return_value = Obj(id=11, org_id=1)
        mock_list.return_value = [
            Obj(id=1, org_id=1, schedule_id=11, weekday=0, start_time="09:00:00", end_time="17:00:00", required_staff_count=2, notes=None),
            Obj(id=2, org_id=1, schedule_id=11, weekday=2, start_time="10:00:00", end_time="18:00:00", required_staff_count=1, notes="X"),
        ]
        resp = self.client.get(f"{self.base}/11/weekly-template")
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["weekday"], 0)
        self.assertEqual(data[1]["notes"], "X")

    @patch("weeklytemplate.router.get_schedule_for_org")
    def test_list_weekly_template_404_wrong_org(self, mock_sched):
        mock_sched.return_value = None
        resp = self.client.get(f"{self.base}/999/weekly-template")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "Schedule not found")

    # ---------------- UPSERT (PUT) ----------------

    @patch("weeklytemplate.router.get_schedule_for_org")
    @patch("weeklytemplate.router.service.upsert_weekly_template")
    def test_save_weekly_template_200(self, mock_upsert, mock_sched):
        mock_sched.return_value = Obj(id=11, org_id=1)
        mock_upsert.return_value = [
            Obj(id=5, org_id=1, schedule_id=11, weekday=0, start_time="09:00:00", end_time="17:00:00", required_staff_count=2, notes=None),
        ]
        payload = {"items": [{"weekday": 0, "start_time": "09:00:00", "end_time": "17:00:00", "required_staff_count": 2}]}
        resp = self.client.put(f"{self.base}/11/weekly-template", json=payload)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()[0]["id"], 5)

    @patch("weeklytemplate.router.get_schedule_for_org")
    @patch("weeklytemplate.router.service.upsert_weekly_template")
    def test_save_weekly_template_409_conflict(self, mock_upsert, mock_sched):
        mock_sched.return_value = Obj(id=11, org_id=1)
        mock_upsert.side_effect = IntegrityError("stmt", "params", Exception("dup"))
        payload = {"items": [{"weekday": 1, "start_time": "08:00:00", "end_time": "16:00:00"}]}
        resp = self.client.put(f"{self.base}/11/weekly-template", json=payload)
        self.assertEqual(resp.status_code, 409, resp.text)
        self.assertEqual(resp.json()["detail"], "Weekly template contains conflicting slots")

    # ---------------- PATCH single row ----------------

    @patch("weeklytemplate.router.get_schedule_for_org")
    @patch("weeklytemplate.router.service.update_weekly_template_row")
    def test_patch_weekly_template_row_200(self, mock_update, mock_sched):
        mock_sched.return_value = Obj(id=11, org_id=1)
        mock_update.return_value = Obj(
            id=7, org_id=1, schedule_id=11, weekday=0, start_time="09:00:00", end_time="17:00:00",
            required_staff_count=3, notes="updated"
        )
        resp = self.client.patch(
            f"{self.base}/11/weekly-template/7",
            json={"required_staff_count": 3, "notes": "updated"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["id"], 7)
        self.assertEqual(body["required_staff_count"], 3)

    @patch("weeklytemplate.router.get_schedule_for_org")
    @patch("weeklytemplate.router.service.update_weekly_template_row")
    def test_patch_weekly_template_row_404(self, mock_update, mock_sched):
        mock_sched.return_value = Obj(id=11, org_id=1)
        mock_update.return_value = None
        resp = self.client.patch(f"{self.base}/11/weekly-template/999", json={"notes": "nope"})
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "Template row not found")

    @patch("weeklytemplate.router.get_schedule_for_org")
    @patch("weeklytemplate.router.service.update_weekly_template_row")
    def test_patch_weekly_template_row_409_conflict(self, mock_update, mock_sched):
        mock_sched.return_value = Obj(id=11, org_id=1)
        mock_update.side_effect = IntegrityError("stmt", "params", Exception("dup"))
        resp = self.client.patch(f"{self.base}/11/weekly-template/7", json={"weekday": 1})
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["detail"], "Another template row already occupies this slot")

    # ---------------- DELETE single row ----------------

    @patch("weeklytemplate.router.get_schedule_for_org")
    @patch("weeklytemplate.router.service.delete_weekly_template_row")
    def test_delete_weekly_template_row_200(self, mock_delete, mock_sched):
        mock_sched.return_value = Obj(id=11, org_id=1)
        mock_delete.return_value = True
        resp = self.client.delete(f"{self.base}/11/weekly-template/7")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json(), {"message": "weekly template row deleted"})

    @patch("weeklytemplate.router.get_schedule_for_org")
    @patch("weeklytemplate.router.service.delete_weekly_template_row")
    def test_delete_weekly_template_row_404(self, mock_delete, mock_sched):
        mock_sched.return_value = Obj(id=11, org_id=1)
        mock_delete.return_value = False
        resp = self.client.delete(f"{self.base}/11/weekly-template/999")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "Template row not found")

    # ---------------- GENERATE ----------------

    @patch("weeklytemplate.router.get_schedule_for_org")
    @patch("weeklytemplate.router.service.generate_from_weekly_template")
    def test_generate_from_template_200(self, mock_gen, mock_sched):
        mock_sched.return_value = Obj(id=11, org_id=1)
        mock_gen.return_value = {"created": 4, "replaced": 2, "skipped": 0}
        payload = {"start_date": "2025-10-27", "end_date": "2025-11-02", "policy": "replace"}
        resp = self.client.post(f"{self.base}/11/weekly-template/generate", json=payload)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["created"], 4)

    @patch("weeklytemplate.router.get_schedule_for_org")
    def test_generate_from_template_404_wrong_org(self, mock_sched):
        mock_sched.return_value = None
        payload = {"start_date": "2025-10-27", "end_date": "2025-11-02", "policy": "replace"}
        resp = self.client.post(f"{self.base}/999/weekly-template/generate", json=payload)
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "Schedule not found")


if __name__ == "__main__":
    unittest.main(verbosity=2)
