import unittest
from types import SimpleNamespace as Obj
from unittest.mock import patch
from fastapi.testclient import TestClient

from main import app
from core.database import get_db
from auth.services.auth_service import get_current_active_user
from authz.deps import require_manager


class PreferenceRouterTests(unittest.TestCase):
    def setUp(self):
        class FakeDB:
            def rollback(self): pass
        def _fake_db():
            yield FakeDB()

        app.dependency_overrides[get_db] = _fake_db
        # pretend caller belongs to org 1
        app.dependency_overrides[get_current_active_user] = lambda: Obj(org_id=1)
        app.dependency_overrides[require_manager] = lambda: None

        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_active_user, None)
        app.dependency_overrides.pop(require_manager, None)

    # ---------------- LIST ----------------

    @patch("preference.router.service.get_preferences")
    def test_get_preferences_by_org_happy_path(self, mock_get):
        mock_get.return_value = [
            Obj(
                id=11, employee_id=5, weekday=2,
                start_time="09:00:00", end_time="12:00:00",
                role_id=None, location_id=None,
                weight=3, do_not_schedule=False, notes=None,
                active_start=None, active_end=None,
            )
        ]
        resp = self.client.get("/api/preferences")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(
            resp.json(),
            [{
                "id": 11,
                "employee_id": 5,
                "weekday": 2,
                "start_time": "09:00:00",
                "end_time": "12:00:00",
                "role_id": None,
                "location_id": None,
                "weight": 3,
                "do_not_schedule": False,
                "notes": None,
                "active_start": None,
                "active_end": None,
            }],
        )

    @patch("preference.router.service.get_preferences")
    def test_get_preferences_defaults_to_user_org(self, mock_get):
        mock_get.return_value = []
        resp = self.client.get("/api/preferences")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    # ---------------- CREATE ----------------

    @patch("preference.router.service.create_preference")
    def test_create_preference_201(self, mock_create):
        mock_create.return_value = Obj(
            id=100, employee_id=5, weekday=1,
            start_time="10:00:00", end_time="14:00:00",
            role_id=None, location_id=None,
            weight=2, do_not_schedule=False, notes="morning pls",
            active_start=None, active_end=None,
        )
        body = {
            "employee_id": 5,
            "weekday": 1,
            "start_time": "10:00:00",
            "end_time": "14:00:00",
            "weight": 2,
            "do_not_schedule": False,
            "notes": "morning pls"
        }
        resp = self.client.post("/api/preferences", json=body)
        self.assertEqual(resp.status_code, 201, resp.text)
        self.assertEqual(resp.json()["id"], 100)

    def test_create_preference_422_if_client_sends_org_id(self):
        body = {
            "employee_id": 5,
            "weekday": 1,
            "start_time": "10:00:00",
            "end_time": "14:00:00",
            "org_id": 999,
        }
        resp = self.client.post("/api/preferences", json=body)
        self.assertEqual(resp.status_code, 422)

    @patch("preference.router.service.create_preference")
    def test_create_preference_409_duplicate(self, mock_create):
        from sqlalchemy.exc import IntegrityError
        mock_create.side_effect = IntegrityError("stmt", "params", Exception("dup"))
        body = {
            "employee_id": 5,
            "weekday": 2,
            "start_time": "09:00:00",
            "end_time": "12:00:00",
        }
        resp = self.client.post("/api/preferences", json=body)
        self.assertEqual(resp.status_code, 409, resp.text)
        self.assertEqual(resp.json()["detail"], "preference already exists for these fields")

    # ---------------- GET /{id} ----------------

    @patch("preference.router.service.get_preference_for_org")
    def test_get_preference_200(self, mock_get_for_org):
        mock_get_for_org.return_value = Obj(
            id=42, employee_id=5, weekday=None,
            start_time=None, end_time=None,
            role_id=7, location_id=None,
            weight=None, do_not_schedule=True, notes="on call block",
            active_start="2025-10-01", active_end="2025-12-31",
        )
        resp = self.client.get("/api/preferences/42")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertTrue(resp.json()["do_not_schedule"])

    @patch("preference.router.service.get_preference_for_org")
    def test_get_preference_404(self, mock_get_for_org):
        mock_get_for_org.return_value = None
        resp = self.client.get("/api/preferences/9999")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "preference not found")

    # ---------------- PATCH /{id} ----------------

    @patch("preference.router.service.update_preference")
    @patch("preference.router.service.get_preference_for_org")
    def test_update_preference_200(self, mock_get_for_org, mock_update):
        mock_get_for_org.return_value = Obj(id=1)
        mock_update.return_value = Obj(
            id=1, employee_id=5, weekday=3,
            start_time="12:00:00", end_time="16:00:00",
            role_id=None, location_id=None,
            weight=5, do_not_schedule=False, notes=None,
            active_start=None, active_end=None,
        )
        patch_body = {"weekday": 3, "start_time": "12:00:00", "end_time": "16:00:00", "weight": 5}
        resp = self.client.patch("/api/preferences/1", json=patch_body)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["weekday"], 3)

    @patch("preference.router.service.get_preference_for_org")
    def test_update_preference_404(self, mock_get_for_org):
        mock_get_for_org.return_value = None
        resp = self.client.patch("/api/preferences/123", json={"notes": "hi"})
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "preference not found")

    # ---------------- DELETE /{id} ----------------

    @patch("preference.router.service.delete_preference")
    @patch("preference.router.service.get_preference_for_org")
    def test_delete_preference_200(self, mock_get_for_org, mock_delete):
        mock_get_for_org.return_value = Obj(id=1)
        mock_delete.return_value = True
        resp = self.client.delete("/api/preferences/1")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json(), {"message": "preference deleted"})

    @patch("preference.router.service.get_preference_for_org")
    def test_delete_preference_404_missing(self, mock_get_for_org):
        mock_get_for_org.return_value = None
        resp = self.client.delete("/api/preferences/999")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "preference not found")

    @patch("preference.router.service.delete_preference")
    @patch("preference.router.service.get_preference_for_org")
    def test_delete_preference_200_service_false(self, mock_get_for_org, mock_delete):
        mock_get_for_org.return_value = Obj(id=1)
        mock_delete.return_value = False
        resp = self.client.delete("/api/preferences/1")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"message": "preference deleted"})
