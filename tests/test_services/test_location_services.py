# tests/test_services/test_location_service.py
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.database import Base
from sqlalchemy.orm import Session
from organization.models import Organization
from location.models import Location
from location import service
from location.schemas import LocationCreate, LocationUpdateIn


class Obj:
    """Simple attribute container for payload mocks."""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class LocationServiceTests(unittest.TestCase):
    def setUp(self):
        # Fresh in-memory DB
        self.engine = create_engine("sqlite:///:memory:", future=True)
        # IMPORTANT: models must be imported before create_all so tables exist
        Base.metadata.create_all(self.engine)

        TestingSession = sessionmaker(bind=self.engine, future=True)
        self.db = TestingSession()

        # --- seed orgs ---
        org1 = Organization(name="Org One", timezone="Atlantic/Reykjavik")
        org2 = Organization(name="Org Two", timezone="Atlantic/Reykjavik")
        self.db.add_all([org1, org2])
        self.db.flush()
        self.org1_id = org1.id
        self.org2_id = org2.id

        # --- seed locations ---
        l1 = Location(org_id=self.org1_id, name="HQ")
        l2 = Location(org_id=self.org1_id, name="Warehouse")
        l3 = Location(org_id=self.org2_id, name="Remote Office")
        self.db.add_all([l1, l2, l3])
        self.db.commit()
        self.db.refresh(l1); self.db.refresh(l2); self.db.refresh(l3)

        self.loc_org1_ids = [l1.id, l2.id]
        self.loc_org2_id = l3.id

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    # ---- get_location ----
    def test_get_location_found(self):
        got = service.get_location(self.db, self.loc_org1_ids[0])
        self.assertIsNotNone(got)
        self.assertEqual(got.id, self.loc_org1_ids[0])

    def test_get_location_not_found(self):
        got = service.get_location(self.db, 999999)
        self.assertIsNone(got)

    # ---- get_locations ----

    def test_get_locations_all_for_org(self):
        rows = service.get_locations(self.db, org_id=self.org1_id)
        names = {r.name for r in rows}
        self.assertEqual(names, {"HQ", "Warehouse"})


    # ---- get_location_for_org ----
    def test_get_location_for_org_ok(self):
        target = self.loc_org1_ids[0]
        row = service.get_location_for_org(self.db, target, self.org1_id)
        self.assertIsNotNone(row)
        self.assertEqual(row.id, target)
        self.assertEqual(row.org_id, self.org1_id)

    def test_get_location_for_org_mismatch(self):
        target = self.loc_org1_ids[0]  # belongs to org1
        row = service.get_location_for_org(self.db, target, self.org2_id)
        self.assertIsNone(row)

    # ---- create_location ----
    def test_create_location_inserts_and_returns(self):
        # use the internal DTO that the router would build
        payload = LocationCreate(org_id=self.org1_id, name="Clinic")

        created = service.create_location(self.db, payload)
        self.assertIsInstance(created.id, int)

        again = service.get_location(self.db, created.id)
        self.assertIsNotNone(again)
        self.assertEqual(again.name, "Clinic")

    # ---- update_location ----
    def test_update_location_name_only(self):
        target = self.loc_org1_ids[0]
        updated = service.update_location(self.db, target, LocationUpdateIn(name="HQ North"))
        self.assertIsNotNone(updated)
        self.assertEqual(updated.name, "HQ North")
        # org_id should remain unchanged
        self.assertEqual(updated.org_id, self.org1_id)

    def test_update_location_not_found_returns_none(self):
        res = service.update_location(self.db, 999999, LocationUpdateIn(name="X"))
        self.assertIsNone(res)

    def test_update_location_ignores_org_id_mutation(self):
        target = self.loc_org1_ids[1]
        before = service.get_location(self.db, target)
        # Attempt to move to another org via payload (should be ignored)
        res = service.update_location(self.db, target, LocationUpdateIn(org_id=self.org2_id, name="Warehouse East"))
        self.assertIsNotNone(res)
        self.assertEqual(res.name, "Warehouse East")
        self.assertEqual(res.org_id, before.org_id)  # unchanged

    # ---- delete_location ----
    def delete_location(db: Session, loc_id: int) -> bool:
        row = db.get(Location, loc_id)
        if not row:
            return False
        db.delete(row)
        db.commit()
        return True


if __name__ == "__main__":
    unittest.main()
