# tests/test_routers/test_assignment_router.py

import unittest
from types import SimpleNamespace as Obj
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from main import app
from core.database import get_db
from auth.services.auth_service import get_current_active_user
from authz.deps import require_manager


class AssignmentRouterTests(unittest.TestCase):
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

    @patch("assignment.router.service.get_assignments")
    def test_list_assignments_happy_path(self, mock_list):
        mock_list.return_value = [
            Obj(shift_id=100, employee_id=10),
            Obj(shift_id=101, employee_id=11),
        ]
        resp = self.client.get("/api/assignments")
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["shift_id"], 100)

    @patch("assignment.router.service.get_assignments")
    def test_list_assignments_with_filters(self, mock_list):
        mock_list.return_value = [Obj(shift_id=100, employee_id=10)]
        resp = self.client.get("/api/assignments?shift_id=100&employee_id=10")
        self.assertEqual(resp.status_code, 200)
        out = resp.json()
        self.assertEqual(out[0]["shift_id"], 100)
        self.assertEqual(out[0]["employee_id"], 10)

    # --- GET /{shift_id}/{employee_id} ---

    @patch("assignment.router.service.get_assignment_for_org")
    def test_get_assignment_200(self, mock_get_for_org):
        mock_get_for_org.return_value = Obj(shift_id=100, employee_id=10)
        resp = self.client.get("/api/assignments/100/10")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["employee_id"], 10)

    @patch("assignment.router.service.get_assignment_for_org")
    def test_get_assignment_404(self, mock_get_for_org):
        mock_get_for_org.return_value = None
        resp = self.client.get("/api/assignments/999/888")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "assignment not found")

    # --- POST ---

    @patch("assignment.router.service.create_assignment")
    def test_create_assignment_201(self, mock_create):
        mock_create.return_value = Obj(shift_id=100, employee_id=10)
        resp = self.client.post(
            "/api/assignments",
            json={"shift_id": 100, "employee_id": 10},
        )
        self.assertEqual(resp.status_code, 201, resp.text)
        body = resp.json()
        self.assertEqual(body["shift_id"], 100)
        self.assertEqual(body["employee_id"], 10)

    @patch("assignment.router.service.create_assignment")
    def test_create_assignment_409_duplicate(self, mock_create):
        mock_create.side_effect = IntegrityError("stmt", "params", Exception("dup"))
        resp = self.client.post(
            "/api/assignments",
            json={"shift_id": 100, "employee_id": 10},
        )
        self.assertEqual(resp.status_code, 409, resp.text)
        self.assertEqual(resp.json()["detail"], "assignment already exists for this shift/employee")

    # --- PATCH /{shift_id}/{employee_id} ---

    @patch("assignment.router.service.update_assignment")
    @patch("assignment.router.service.get_assignment_for_org")
    def test_update_assignment_200(self, mock_get_for_org, mock_update):
        # Note: decorator closest to the function is the FIRST arg
        mock_get_for_org.return_value = Obj(shift_id=100, employee_id=10)
        mock_update.return_value = Obj(shift_id=100, employee_id=10)

        resp = self.client.patch(
            "/api/assignments/100/10",
            json={},  # AssignmentUpdate currently has no fields
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertEqual(data["shift_id"], 100)
        self.assertEqual(data["employee_id"], 10)

    @patch("assignment.router.service.get_assignment_for_org")
    def test_update_assignment_404(self, mock_get_for_org):
        mock_get_for_org.return_value = None
        resp = self.client.patch("/api/assignments/100/10", json={})
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "assignment not found")

    @patch("assignment.router.service.update_assignment")
    @patch("assignment.router.service.get_assignment_for_org")
    def test_update_assignment_409(self, mock_get_for_org, mock_update):
        mock_get_for_org.return_value = Obj(shift_id=100, employee_id=10)
        mock_update.side_effect = IntegrityError("stmt", "params", Exception("dup"))
        resp = self.client.patch("/api/assignments/100/10", json={})
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["detail"], "assignment already exists for this shift/employee")

    # --- DELETE /{shift_id}/{employee_id} ---

    @patch("assignment.router.service.delete_assignment")
    @patch("assignment.router.service.get_assignment_for_org")
    def test_delete_assignment_200(self, mock_get_for_org, mock_delete):
        # Closest decorator (get_assignment_for_org) -> first arg
        mock_get_for_org.return_value = Obj(shift_id=100, employee_id=10)
        mock_delete.return_value = None

        resp = self.client.delete("/api/assignments/100/10")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json(), {"message": "assignment deleted"})

    @patch("assignment.router.service.get_assignment_for_org")
    def test_delete_assignment_404(self, mock_get_for_org):
        mock_get_for_org.return_value = None
        resp = self.client.delete("/api/assignments/100/10")
        self.assertEqual(resp.status_code, 404, resp.text)
        self.assertEqual(resp.json()["detail"], "assignment not found")
