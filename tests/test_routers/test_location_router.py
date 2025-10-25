import unittest
from types import SimpleNamespace as Obj
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError


from main import app
from core.database import get_db
from auth.services.auth_service import get_current_active_user
from authz.deps import require_manager


class LocationRouterTests(unittest.TestCase):
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

    @patch("location.router.service.get_locations")
    def test_get_locations_by_org_happy_path(self, mock_get):
        mock_get.return_value = [Obj(id=1, org_id=1, name="HQ")]
        resp = self.client.get("/api/locations")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json(), [{"id": 1, "org_id": 1, "name": "HQ"}])


    @patch("location.router.service.get_locations")
    def test_get_locations_query_param_defaults_to_user_org(self, mock_get_locations):
        mock_get_locations.return_value = [Obj(id=1, org_id=1, name="HQ")]
        resp = self.client.get("/api/locations")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["org_id"], 1)

    # --- CREATE ---

    @patch("location.router.service.create_location")
    def test_create_location_201(self, mock_create):
        mock_create.return_value = Obj(id=10, org_id=1, name="Clinic")
        resp = self.client.post("/api/locations", json={"name": "Clinic"})
        self.assertEqual(resp.status_code, 201)

    def test_create_location_422_if_client_sends_org_id(self):
        # extra field should be rejected by the request model
        resp = self.client.post("/api/locations", json={"name": "Clinic", "org_id": 2})
        self.assertEqual(resp.status_code, 422)

    @patch("location.router.service.create_location")
    def test_create_location_409_duplicate_name(self, mock_create):
        # Simulate unique constraint violation
        
        mock_create.side_effect = IntegrityError("stmt", "params", Exception("dup"))

        resp = self.client.post("/api/locations", json={"name": "Clinic"})
        self.assertEqual(resp.status_code, 409, resp.text)
        self.assertEqual(resp.json()["detail"], "Location name already exists in this organization")


    # --- GET /{id} ---

    @patch("location.router.service.get_location_for_org")
    def test_get_location_200(self, mock_get_for_org):
        mock_get_for_org.return_value = Obj(id=1, org_id=1, name="HQ")
        resp = self.client.get("/api/locations/1")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["name"], "HQ")

    @patch("location.router.service.get_location_for_org")
    def test_get_location_404(self, mock_get_for_org):
        mock_get_for_org.return_value = None
        resp = self.client.get("/api/locations/999")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "Location not found")

    # --- PATCH /{id} ---

    @patch("location.router.service.update_location")
    @patch("location.router.service.get_location_for_org")
    def test_update_location_200(self, mock_get_for_org, mock_update):
        mock_get_for_org.return_value = Obj(id=1, org_id=1, name="HQ")
        mock_update.return_value = Obj(id=1, org_id=1, name="HQ North")

        resp = self.client.patch("/api/locations/1", json={"name": "HQ North"})
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["name"], "HQ North")

    @patch("location.router.service.get_location_for_org")
    def test_update_location_404(self, mock_get_for_org):
        mock_get_for_org.return_value = None
        resp = self.client.patch("/api/locations/999", json={"name": "Nope"})
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "Location not found")

    # --- DELETE /{id} ---

    @patch("location.router.service.delete_location")
    @patch("location.router.service.get_location_for_org")
    def test_delete_location_200(self, mock_get_for_org, mock_delete):
        mock_get_for_org.return_value = Obj(id=1, org_id=1, name="HQ")
        mock_delete.return_value = True
        resp = self.client.delete("/api/locations/1")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json(), {"message": "Location deleted"})

    @patch("location.router.service.get_location_for_org")
    def test_delete_location_404_missing(self, mock_get_for_org):
        mock_get_for_org.return_value = None
        resp = self.client.delete("/api/locations/999")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "Location not found")

    @patch("location.router.service.delete_location")
    @patch("location.router.service.get_location_for_org")
    def test_delete_location_404_service_false(self, mock_get_for_org, mock_delete):
        mock_get_for_org.return_value = Obj(id=1, org_id=1, name="HQ")
        mock_delete.return_value = False

        resp = self.client.delete("/api/locations/1")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"message": "Location deleted"})

