import unittest
from types import SimpleNamespace as Obj
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from main import app
from core.database import get_db
from auth.services.auth_service import get_current_active_user
from authz.deps import require_manager


class UnavailabilityRouterTests(unittest.TestCase):
    def setUp(self):
        class FakeDB:
            def rollback(self): pass
        def _fake_db():
            yield FakeDB()

        app.dependency_overrides[get_db] = _fake_db
        app.dependency_overrides[get_current_active_user] = lambda: Obj(org_id=1, id=123)
        app.dependency_overrides[require_manager] = lambda: None

        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_active_user, None)
        app.dependency_overrides.pop(require_manager, None)

    # --- LIST ---

    @patch("unavailability.router.service.get_unavailabilities")
    def test_list_unavailability_happy_path(self, mock_list):
        mock_list.return_value = [
            Obj(id=1, employee_id=10, start_at="2025-10-18T09:00:00+00:00", end_at="2025-10-18T12:00:00+00:00", reason=None),
            Obj(id=2, employee_id=11, start_at="2025-10-19T14:00:00+00:00", end_at="2025-10-19T18:00:00+00:00", reason="Doctor"),
        ]
        resp = self.client.get("/api/unavailability")
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["employee_id"], 10)

    @patch("unavailability.router.service.get_unavailabilities")
    def test_list_unavailability_filter_employee(self, mock_list):
        mock_list.return_value = [Obj(id=3, employee_id=42, start_at="2025-10-20T09:00:00Z", end_at="2025-10-20T11:00:00Z", reason=None)]
        resp = self.client.get("/api/unavailability?employee_id=42")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()[0]["employee_id"], 42)

    # --- GET /{id} ---

    @patch("unavailability.router.service.get_unavailability_for_org")
    def test_get_unavailability_200(self, mock_get_for_org):
        mock_get_for_org.return_value = Obj(id=5, employee_id=10, start_at="2025-10-21T09:00:00Z", end_at="2025-10-21T12:00:00Z", reason=None)
        resp = self.client.get("/api/unavailability/5")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["id"], 5)

    @patch("unavailability.router.service.get_unavailability_for_org")
    def test_get_unavailability_404(self, mock_get_for_org):
        mock_get_for_org.return_value = None
        resp = self.client.get("/api/unavailability/999")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "unavailability not found")

    # --- POST ---

    @patch("unavailability.router.service.create_unavailability")
    def test_create_unavailability_201(self, mock_create):
        mock_create.return_value = Obj(
            id=7, employee_id=10,
            start_at="2025-10-22T09:00:00Z",
            end_at="2025-10-22T11:00:00Z",
            reason="Dentist"
        )
        resp = self.client.post(
            "/api/unavailability",
            json={
                "employee_id": 10,
                "start_at": "2025-10-22T09:00:00Z",
                "end_at": "2025-10-22T11:00:00Z",
                "reason": "Dentist",
            },
        )
        self.assertEqual(resp.status_code, 201, resp.text)
        body = resp.json()
        self.assertEqual(body["employee_id"], 10)
        self.assertEqual(body["reason"], "Dentist")

    def test_create_unavailability_422_invalid_window(self):
        # start_at after end_at -> Pydantic validator should 422
        resp = self.client.post(
            "/api/unavailability",
            json={
                "employee_id": 10,
                "start_at": "2025-10-22T12:00:00Z",
                "end_at": "2025-10-22T11:00:00Z",
            },
        )
        self.assertEqual(resp.status_code, 422, resp.text)

    @patch("unavailability.router.service.create_unavailability")
    def test_create_unavailability_409_duplicate(self, mock_create):
        mock_create.side_effect = IntegrityError("stmt", "params", Exception("dup"))
        resp = self.client.post(
            "/api/unavailability",
            json={
                "employee_id": 10,
                "start_at": "2025-10-22T09:00:00Z",
                "end_at": "2025-10-22T11:00:00Z",
            },
        )
        self.assertEqual(resp.status_code, 409, resp.text)
        self.assertEqual(resp.json()["detail"], "unavailability already exists for this window")

    # --- PATCH /{id} ---

    @patch("unavailability.router.service.update_unavailability")
    @patch("unavailability.router.service.get_unavailability_for_org")
    def test_update_unavailability_200(self, mock_get_for_org, mock_update):
        mock_get_for_org.return_value = Obj(id=8, employee_id=10, start_at="2025-10-23T09:00:00Z", end_at="2025-10-23T11:00:00Z", reason=None)
        mock_update.return_value = Obj(id=8, employee_id=10, start_at="2025-10-23T10:00:00Z", end_at="2025-10-23T12:00:00Z", reason="Errand")
        resp = self.client.patch(
            "/api/unavailability/8",
            json={"start_at": "2025-10-23T10:00:00Z", "end_at": "2025-10-23T12:00:00Z", "reason": "Errand"},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["reason"], "Errand")

    @patch("unavailability.router.service.get_unavailability_for_org")
    def test_update_unavailability_404(self, mock_get_for_org):
        mock_get_for_org.return_value = None
        resp = self.client.patch("/api/unavailability/999", json={"reason": "Nope"})
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "unavailability not found")

    @patch("unavailability.router.service.update_unavailability")
    @patch("unavailability.router.service.get_unavailability_for_org")
    def test_update_unavailability_409_duplicate(self, mock_get_for_org, mock_update):
        mock_get_for_org.return_value = Obj(id=9, employee_id=10, start_at="2025-10-24T09:00:00Z", end_at="2025-10-24T11:00:00Z", reason=None)
        mock_update.side_effect = IntegrityError("stmt", "params", Exception("dup"))
        resp = self.client.patch("/api/unavailability/9", json={"start_at": "2025-10-24T09:30:00Z", "end_at": "2025-10-24T11:30:00Z"})
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["detail"], "unavailability already exists for this window")

    # --- DELETE /{id} ---

    @patch("unavailability.router.service.delete_unavailability")
    @patch("unavailability.router.service.get_unavailability_for_org")
    def test_delete_unavailability_200(self, mock_get_for_org, mock_delete):
        mock_get_for_org.return_value = Obj(id=12, employee_id=10, start_at="2025-10-25T09:00:00Z", end_at="2025-10-25T11:00:00Z", reason=None)
        mock_delete.return_value = None
        resp = self.client.delete("/api/unavailability/12")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json(), {"message": "unavailability deleted"})

    @patch("unavailability.router.service.get_unavailability_for_org")
    def test_delete_unavailability_404(self, mock_get_for_org):
        mock_get_for_org.return_value = None
        resp = self.client.delete("/api/unavailability/404")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "unavailability not found")
