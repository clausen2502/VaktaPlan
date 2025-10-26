import unittest
from types import SimpleNamespace as Obj
from unittest.mock import patch
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from main import app
from core.database import get_db
from auth.services.auth_service import get_current_active_user
from authz.deps import require_manager


class OrganizationRouterTests(unittest.TestCase):
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

    @patch("organization.router.service.list_organizations")
    def test_list_organizations_happy_path(self, mock_list):
        mock_list.return_value = [
            Obj(id=1, name="Org A", timezone="Atlantic/Reykjavik"),
            Obj(id=2, name="Org B", timezone="Atlantic/Reykjavik"),
        ]
        resp = self.client.get("/api/organizations")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(
            resp.json(),
            [
                {"id": 1, "name": "Org A", "timezone": "Atlantic/Reykjavik"},
                {"id": 2, "name": "Org B", "timezone": "Atlantic/Reykjavik"},
            ],
        )

    # --- GET /me ---

    @patch("organization.router.service.get_organization")
    def test_get_my_organization_200(self, mock_get):
        mock_get.return_value = Obj(id=1, name="My Org", timezone="Atlantic/Reykjavik")
        resp = self.client.get("/api/organizations/me")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["id"], 1)
        self.assertEqual(resp.json()["name"], "My Org")

    @patch("organization.router.service.get_organization")
    def test_get_my_organization_404(self, mock_get):
        mock_get.return_value = None
        resp = self.client.get("/api/organizations/me")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "organization not found")

    # --- GET /{id} ---

    @patch("organization.router.service.get_organization")
    def test_get_organization_200(self, mock_get):
        mock_get.return_value = Obj(id=9, name="Target Org", timezone="Atlantic/Reykjavik")
        resp = self.client.get("/api/organizations/9")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["name"], "Target Org")

    @patch("organization.router.service.get_organization")
    def test_get_organization_404(self, mock_get):
        mock_get.return_value = None
        resp = self.client.get("/api/organizations/999")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "organization not found")

    # --- CREATE ---

    @patch("organization.router.service.create_organization")
    def test_create_organization_201(self, mock_create):
        mock_create.return_value = Obj(id=10, name="CreateCo", timezone="Atlantic/Reykjavik")
        resp = self.client.post("/api/organizations", json={"name": "CreateCo"})
        self.assertEqual(resp.status_code, 201, resp.text)
        body = resp.json()
        self.assertEqual(body["name"], "CreateCo")
        self.assertEqual(body["timezone"], "Atlantic/Reykjavik")

    def test_create_organization_422_if_client_sends_extra_fields(self):
        # extra field should be rejected by the request model (extra="forbid")
        resp = self.client.post("/api/organizations", json={"name": "CreateCo", "id": 77})
        self.assertEqual(resp.status_code, 422)

    @patch("organization.router.service.create_organization")
    def test_create_organization_409_duplicate_name(self, mock_create):
        # Simulate unique constraint violation
        mock_create.side_effect = IntegrityError("stmt", "params", Exception("dup"))
        resp = self.client.post("/api/organizations", json={"name": "DupeCo"})
        self.assertEqual(resp.status_code, 409, resp.text)
        self.assertEqual(resp.json()["detail"], "organization name already exists")

    # --- PATCH /{id} ---

    @patch("organization.router.service.update_organization")
    def test_update_organization_200(self, mock_update):
        mock_update.return_value = Obj(id=1, name="Patched", timezone="Atlantic/Reykjavik")
        resp = self.client.patch("/api/organizations/1", json={"name": "Patched"})
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["name"], "Patched")

    @patch("organization.router.service.update_organization")
    def test_update_organization_404(self, mock_update):
        mock_update.side_effect = HTTPException(status_code=404, detail="organization not found")
        resp = self.client.patch("/api/organizations/1", json={"name": "Nope"})
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "organization not found")

    def test_update_organization_403_when_path_id_differs(self):
        resp = self.client.patch("/api/organizations/999", json={"name": "Nope"})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["detail"], "forbidden: cannot update another organization")

    @patch("organization.router.service.update_organization")
    def test_update_organization_409_duplicate_name(self, mock_update):
        from fastapi import HTTPException
        mock_update.side_effect = HTTPException(status_code=409, detail="organization name already exists")

        resp = self.client.patch("/api/organizations/1", json={"name": "Dupe"})
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["detail"], "organization name already exists")

    # --- DELETE /{id} ---

    @patch("organization.router.service.delete_organization")
    @patch("organization.router.service.get_organization")
    def test_delete_organization_200(self, mock_get, mock_delete):
        mock_get.return_value = Obj(id=1, name="KillMe", timezone="Atlantic/Reykjavik")
        mock_delete.return_value = None
        resp = self.client.delete("/api/organizations/1")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json(), {"message": "organization deleted"})

    @patch("organization.router.service.get_organization")
    def test_delete_organization_404_missing(self, mock_get):
        # our override user has org_id = 1
        mock_get.return_value = None  # simulate missing org
        resp = self.client.delete("/api/organizations/1")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "organization not found")
    
    def test_delete_organization_403_when_path_id_differs(self):
        resp = self.client.delete("/api/organizations/999")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["detail"], "forbidden: cannot delete another organization")



