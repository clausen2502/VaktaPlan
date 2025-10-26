import unittest
from types import SimpleNamespace as Obj
from unittest.mock import patch
from fastapi.testclient import TestClient
from datetime import datetime

from main import app
from core.database import get_db
from auth.services.auth_service import get_current_active_user
from authz.deps import require_manager


class PublicationRouterTests(unittest.TestCase):
    def setUp(self):
        class FakeDB:
            def rollback(self): pass
        def _fake_db():
            yield FakeDB()

        app.dependency_overrides[get_db] = _fake_db
        # pretend caller belongs to org 1 and has user id 77
        app.dependency_overrides[get_current_active_user] = lambda: Obj(org_id=1, id=77)
        app.dependency_overrides[require_manager] = lambda: None

        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_active_user, None)
        app.dependency_overrides.pop(require_manager, None)

    # ---------------- LIST ----------------

    @patch("publication.router.service.get_publications")
    def test_list_publications_defaults_to_user_org(self, mock_get):
        mock_get.return_value = []
        resp = self.client.get("/api/publications")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    # ---------------- GET /{id} ----------------

    @patch("publication.router.service.get_publication_for_org")
    def test_get_publication_200(self, mock_get_for_org):
        mock_get_for_org.return_value = Obj(
            id=42, org_id=1,
            range_start="2025-10-01",
            range_end="2025-10-07",
            version=1,
            user_id=77,
            published_at="2025-10-01T09:00:00+00:00",
        )
        resp = self.client.get("/api/publications/42")
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["id"], 42)
        self.assertEqual(body["version"], 1)

    @patch("publication.router.service.get_publication_for_org")
    def test_get_publication_404(self, mock_get_for_org):
        mock_get_for_org.return_value = None
        resp = self.client.get("/api/publications/9999")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "publication not found")

    # ---------------- CREATE ----------------

    @patch("publication.router.service.create_publication")
    def test_create_publication_201(self, mock_create):
        mock_create.return_value = Obj(
            id=100, org_id=1,
            range_start="2025-11-01",
            range_end="2025-11-07",
            version=3,
            user_id=77,
            published_at="2025-10-31T20:00:00+00:00",
        )
        body = {
            "range_start": "2025-11-01",
            "range_end": "2025-11-07",
            "version": 3
        }
        resp = self.client.post("/api/publications", json=body)
        self.assertEqual(resp.status_code, 201, resp.text)
        self.assertEqual(resp.json()["id"], 100)

    def test_create_publication_422_extra_field_rejected(self):
        # org_id/user_id must come from auth, not client
        body = {
            "range_start": "2025-11-01",
            "range_end": "2025-11-07",
            "org_id": 999
        }
        resp = self.client.post("/api/publications", json=body)
        self.assertEqual(resp.status_code, 422)

    @patch("publication.router.service.create_publication")
    def test_create_publication_409_duplicate(self, mock_create):
        from sqlalchemy.exc import IntegrityError
        mock_create.side_effect = IntegrityError("stmt", "params", Exception("dup"))
        body = {
            "range_start": "2025-10-01",
            "range_end": "2025-10-07",
            "version": 1
        }
        resp = self.client.post("/api/publications", json=body)
        self.assertEqual(resp.status_code, 409, resp.text)
        self.assertEqual(
            resp.json()["detail"],
            "publication already exists for this range and version"
        )

    # ---------------- DELETE /{id} ----------------

    @patch("publication.router.service.delete_publication")
    @patch("publication.router.service.get_publication_for_org")
    def test_delete_publication_200(self, mock_get_for_org, mock_delete):
        mock_get_for_org.return_value = Obj(id=1)
        mock_delete.return_value = True
        resp = self.client.delete("/api/publications/1")
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json(), {"message": "publication deleted"})

    @patch("publication.router.service.get_publication_for_org")
    def test_delete_publication_404_missing(self, mock_get_for_org):
        mock_get_for_org.return_value = None
        resp = self.client.delete("/api/publications/999")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "publication not found")

    @patch("publication.router.service.delete_publication")
    @patch("publication.router.service.get_publication_for_org")
    def test_delete_publication_200_service_false(self, mock_get_for_org, mock_delete):
        mock_get_for_org.return_value = Obj(id=1)
        mock_delete.return_value = False
        resp = self.client.delete("/api/publications/1")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"message": "publication deleted"})
