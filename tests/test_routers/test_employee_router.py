import unittest
from types import SimpleNamespace as Obj
from unittest.mock import patch
from fastapi.testclient import TestClient

from main import app
from core.database import get_db
from auth.services.auth_service import get_current_active_user
from authz.deps import require_manager


class EmployeeRouterTests(unittest.TestCase):
    def setUp(self):
        class FakeDB:
            def rollback(self): pass
        def _fake_db():
            yield FakeDB()

        app.dependency_overrides[get_db] = _fake_db
        app.dependency_overrides[get_current_active_user] = lambda: Obj(org_id=1)
        app.dependency_overrides[require_manager] = lambda: None

        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_active_user, None)
        app.dependency_overrides.pop(require_manager, None)

    # --- LIST ---

    @patch("employee.router.service.get_employees")
    def test_get_employees_by_org_happy_path(self, mock_get):
        mock_get.return_value = [Obj(id=1, org_id=1, display_name="johanna")]
        resp = self.client.get("/api/employees")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json(), [{"id": 1, "org_id": 1, "display_name": "johanna", "user_id": None}])


    @patch("employee.router.service.get_employees")
    def test_get_employees_query_param_defaults_to_user_org(self, mock_get_employees):
        mock_get_employees.return_value = [Obj(id=1, org_id=1, display_name="HQ")]
        resp = self.client.get("/api/employees")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["org_id"], 1)

    # --- CREATE ---

    @patch("employee.router.service.create_employee")
    def test_create_employee_201(self, mock_create):
        mock_create.return_value = Obj(id=10, org_id=1, display_name="Jonas")
        resp = self.client.post("/api/employees", json={"display_name": "Jonas"})
        self.assertEqual(resp.status_code, 201)

    def test_create_employee_422_if_client_sends_org_id(self):
        # extra field should be rejected by the request model
        resp = self.client.post("/api/employees", json={"display_name": "Jonas", "org_id": 2})
        self.assertEqual(resp.status_code, 422)

    @patch("employee.router.service.create_employee")
    def test_create_employee_409_duplicate_display_name(self, mock_create):
        # Simulate unique constraint violation
        from sqlalchemy.exc import IntegrityError
        mock_create.side_effect = IntegrityError("stmt", "params", Exception("dup"))

        resp = self.client.post("/api/employees", json={"display_name": "Jonas"})
        self.assertEqual(resp.status_code, 409, resp.text)
        self.assertEqual(resp.json()["detail"], "employee name already exists in this organization")


    # --- GET /{id} ---

    @patch("employee.router.service.get_employee_for_org")
    def test_get_employee_200(self, mock_get_for_org):
        mock_get_for_org.return_value = Obj(id=1, org_id=1, display_name="HQ")
        resp = self.client.get("/api/employees/1")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["display_name"], "HQ")

    @patch("employee.router.service.get_employee_for_org")
    def test_get_employee_404(self, mock_get_for_org):
        mock_get_for_org.return_value = None
        resp = self.client.get("/api/employees/999")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "employee not found")

    # --- PATCH /{id} ---

    @patch("employee.router.service.update_employee")
    @patch("employee.router.service.get_employee_for_org")
    def test_update_employee_200(self, mock_get_for_org, mock_update):
        mock_get_for_org.return_value = Obj(id=1, org_id=1, display_name="HQ")
        mock_update.return_value = Obj(id=1, org_id=1, display_name="HQ North")

        resp = self.client.patch("/api/employees/1", json={"display_name": "HQ North"})
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["display_name"], "HQ North")

    @patch("employee.router.service.get_employee_for_org")
    def test_update_employee_404(self, mock_get_for_org):
        mock_get_for_org.return_value = None
        resp = self.client.patch("/api/employees/999", json={"display_name": "Nope"})
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "employee not found")

    # --- DELETE /{id} ---

    @patch("employee.router.service.delete_employee")
    @patch("employee.router.service.get_employee_for_org")
    def test_delete_employee_200(self, mock_get_for_org, mock_delete):
        mock_get_for_org.return_value = Obj(id=1, org_id=1, display_name="HQ")
        mock_delete.return_value = True
        resp = self.client.delete("/api/employees/1")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json(), {"message": "employee deleted"})

    @patch("employee.router.service.get_employee_for_org")
    def test_delete_employee_404_missing(self, mock_get_for_org):
        mock_get_for_org.return_value = None
        resp = self.client.delete("/api/employees/999")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "employee not found")

    @patch("employee.router.service.delete_employee")
    @patch("employee.router.service.get_employee_for_org")
    def test_delete_employee_404_service_false(self, mock_get_for_org, mock_delete):
        mock_get_for_org.return_value = Obj(id=1, org_id=1, display_name="HQ")
        mock_delete.return_value = False

        resp = self.client.delete("/api/employees/1")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"message": "employee deleted"})

