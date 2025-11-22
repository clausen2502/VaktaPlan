import unittest
from types import SimpleNamespace as Obj
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from main import app
from core.database import get_db
from auth.services.auth_service import get_current_active_user
from authz.deps import require_manager


class JobRoleRouterTests(unittest.TestCase):
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

    @patch("jobrole.router.service.get_jobroles")
    def test_get_jobroles_by_org_happy_path(self, mock_get):
        mock_get.return_value = [Obj(id=1, org_id=1, name="Nurse")]
        resp = self.client.get("/api/jobroles")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json(), [{"id": 1, "org_id": 1, "name": "Nurse", "weekly_hours_cap": None}])

    @patch("jobrole.router.service.get_jobroles")
    def test_get_jobroles_defaults_to_user_org(self, mock_get):
        mock_get.return_value = [Obj(id=1, org_id=1, name="Nurse")]
        resp = self.client.get("/api/jobroles")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["org_id"], 1)

    # --- CREATE ---

    @patch("jobrole.router.service.create_jobrole")
    def test_create_jobrole_201(self, mock_create):
        mock_create.return_value = Obj(id=10, org_id=1, name="Receptionist")
        resp = self.client.post("/api/jobroles", json={"name": "Receptionist"})
        self.assertEqual(resp.status_code, 201)

    def test_create_jobrole_422_if_client_sends_org_id(self):
        resp = self.client.post("/api/jobroles", json={"name": "Receptionist", "org_id": 2})
        self.assertEqual(resp.status_code, 422)

    @patch("jobrole.router.service.create_jobrole")
    def test_create_jobrole_409_duplicate_name(self, mock_create):
        mock_create.side_effect = IntegrityError("stmt", "params", Exception("dup"))
        resp = self.client.post("/api/jobroles", json={"name": "Receptionist"})
        self.assertEqual(resp.status_code, 409, resp.text)
        self.assertEqual(resp.json()["detail"], "jobrole name already exists in this organization")

    @patch("jobrole.router.service.create_jobrole")
    def test_create_jobrole_with_weekly_cap(self, mock_create):
        mock_create.return_value = Obj(id=5, org_id=1, name="Barista", weekly_hours_cap=24)

        resp = self.client.post(
            "/api/jobroles",
            headers={"Content-Type": "application/json"},
            json={"name": "Barista", "weekly_hours_cap": 24},
        )

        self.assertEqual(resp.status_code, 201, resp.text)
        body = resp.json()
        self.assertEqual(body["id"], 5)
        self.assertEqual(body["name"], "Barista")
        self.assertEqual(body["weekly_hours_cap"], 24)

    # --- GET /{id} ---

    @patch("jobrole.router.service.get_jobrole_for_org")
    def test_get_jobrole_200(self, mock_get_for_org):
        mock_get_for_org.return_value = Obj(id=1, org_id=1, name="Nurse")
        resp = self.client.get("/api/jobroles/1")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["name"], "Nurse")

    @patch("jobrole.router.service.get_jobrole_for_org")
    def test_get_jobrole_404(self, mock_get_for_org):
        mock_get_for_org.return_value = None
        resp = self.client.get("/api/jobroles/999")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "jobrole not found")

    # --- PATCH /{id} ---

    @patch("jobrole.router.service.update_jobrole")
    @patch("jobrole.router.service.get_jobrole_for_org")
    def test_update_jobrole_200(self, mock_get_for_org, mock_update):
        mock_get_for_org.return_value = Obj(id=1, org_id=1, name="Nurse")
        mock_update.return_value = Obj(id=1, org_id=1, name="Senior Nurse")

        resp = self.client.patch("/api/jobroles/1", json={"name": "Senior Nurse"})
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["name"], "Senior Nurse")

    @patch("jobrole.router.service.get_jobrole_for_org")
    def test_update_jobrole_404(self, mock_get_for_org):
        mock_get_for_org.return_value = None
        resp = self.client.patch("/api/jobroles/999", json={"name": "Nope"})
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "jobrole not found")

    # --- DELETE /{id} ---

    @patch("jobrole.router.service.delete_jobrole")
    @patch("jobrole.router.service.get_jobrole_for_org")
    def test_delete_jobrole_200(self, mock_get_for_org, mock_delete):
        mock_get_for_org.return_value = Obj(id=1, org_id=1, name="Nurse")
        mock_delete.return_value = True
        resp = self.client.delete("/api/jobroles/1")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json(), {"message": "jobrole deleted"})

    @patch("jobrole.router.service.get_jobrole_for_org")
    def test_delete_jobrole_404_missing(self, mock_get_for_org):
        mock_get_for_org.return_value = None
        resp = self.client.delete("/api/jobroles/999")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "jobrole not found")

    @patch("jobrole.router.service.delete_jobrole")
    @patch("jobrole.router.service.get_jobrole_for_org")
    def test_delete_jobrole_service_false_still_200(self, mock_get_for_org, mock_delete):
        mock_get_for_org.return_value = Obj(id=1, org_id=1, name="Nurse")
        mock_delete.return_value = False
        resp = self.client.delete("/api/jobroles/1")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"message": "jobrole deleted"})
