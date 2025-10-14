import unittest
from types import SimpleNamespace as Obj
from unittest.mock import patch
from fastapi.testclient import TestClient

from main import app
from core.database import get_db

class ShiftRouterTests(unittest.TestCase):
    def setUp(self):
        # override DB dependency with a no-op dummy
        def _fake_db():
            yield Obj()
        app.dependency_overrides[get_db] = _fake_db
        self.client = TestClient(app)

    def tearDown(self):
        # clean override
        app.dependency_overrides.pop(get_db, None)

    @patch("shift.router.list_shifts")
    def test_get_shifts_returns_dummy(self, mock_list_shifts):
        mock_list_shifts.return_value = [
            Obj(
                id=1, org_id=1, location_id=1, role_id=1,
                start_at="2025-10-16T09:00:00Z", end_at="2025-10-16T17:00:00Z"
            )
        ]
        route = self.client.get("/api/shifts/")
        self.assertEqual(route.status_code, 200)
        data = route.json()
        self.assertEqual(data[0]["id"], 1)
        self.assertEqual(data[0]["org_id"], 1)

if __name__ == "__main__":
    unittest.main()
