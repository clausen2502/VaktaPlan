import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from core.database import Base
from organization.models import Organization
from organization.service import list_organizations, get_organization, create_organization, update_organization, delete_organization

from organization.schema import OrganizationCreate, OrganizationUpdate


class OrganizationServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # In-memory SQLite for speed & isolation
        cls.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        Base.metadata.create_all(cls.engine)
        cls.SessionLocal = sessionmaker(bind=cls.engine, autoflush=False, autocommit=False, future=True)

    def setUp(self):
        self.db = self.SessionLocal()

    def tearDown(self):
        # Clean tables between tests
        for tbl in reversed(Base.metadata.sorted_tables):
            self.db.execute(tbl.delete())
        self.db.commit()
        self.db.close()

    # ---------- Helpers ----------
    def _seed(self, name="Org A", tz="Atlantic/Reykjavik"):
        org = Organization(name=name, timezone=tz)
        self.db.add(org)
        self.db.commit()
        self.db.refresh(org)
        return org

    # ---------- Tests ----------
    def test_create_ok(self):
        dto = OrganizationCreate(name="Coffee Co", timezone="Atlantic/Reykjavik")
        obj = create_organization(self.db, dto)
        self.assertIsInstance(obj.id, int)
        self.assertEqual(obj.name, "Coffee Co")
        self.assertEqual(obj.timezone, "Atlantic/Reykjavik")

    def test_create_duplicate_name_409(self):
        self._seed(name="Dupe Inc")
        with self.assertRaises(HTTPException) as ctx:
            create_organization(self.db, OrganizationCreate(name="Dupe Inc", timezone="Atlantic/Reykjavik"))
        self.assertEqual(ctx.exception.status_code, 409)

    def test_get_organization(self):
        org = self._seed(name="Target")
        got = get_organization(self.db, org.id)
        self.assertEqual(got.id, org.id)
        self.assertEqual(got.name, "Target")

    def test_list_organizations_sorted(self):
        self._seed(name="Zeta")
        self._seed(name="Alpha")
        names = [o.name for o in list_organizations(self.db)]
        self.assertEqual(names, ["Alpha", "Zeta"])

    def test_update_ok(self):
        org = self._seed(name="Old")
        patch = OrganizationUpdate(name="New", timezone="Atlantic/Reykjavik")
        updated = update_organization(self.db, org.id, patch)
        self.assertEqual(updated.name, "New")

    def test_update_not_found_404(self):
        with self.assertRaises(HTTPException) as ctx:
            update_organization(self.db, 999999, OrganizationUpdate(name="X"))
        self.assertEqual(ctx.exception.status_code, 404)

    def test_update_duplicate_name_409(self):
        a = self._seed(name="A")
        b = self._seed(name="B")
        with self.assertRaises(HTTPException) as ctx:
            update_organization(self.db, b.id, OrganizationUpdate(name="A"))
        self.assertEqual(ctx.exception.status_code, 409)

    def test_delete_ok(self):
        org = self._seed(name="DelMe")
        delete_organization(self.db, org.id)
        self.assertIsNone(get_organization(self.db, org.id))

    def test_delete_noop_when_missing(self):
        # should not raise
        delete_organization(self.db, 12345)
        self.assertTrue(True)



if __name__ == "__main__":
    unittest.main()
