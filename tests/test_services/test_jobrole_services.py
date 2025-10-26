import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.database import Base
from sqlalchemy.orm import Session
from organization.models import Organization
from jobrole.models import JobRole
from jobrole import service
from jobrole.schemas import JobRoleCreate, JobRoleUpdate


class JobRoleServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", future=True)
        Base.metadata.create_all(self.engine)
        TestingSession = sessionmaker(bind=self.engine, future=True)
        self.db: Session = TestingSession()

        # seed orgs
        org1 = Organization(name="Org One", timezone="Atlantic/Reykjavik")
        org2 = Organization(name="Org Two", timezone="Atlantic/Reykjavik")
        self.db.add_all([org1, org2])
        self.db.flush()
        self.org1_id = org1.id
        self.org2_id = org2.id

        # seed jobroles
        r1 = JobRole(org_id=self.org1_id, name="Nurse")
        r2 = JobRole(org_id=self.org1_id, name="Receptionist")
        r3 = JobRole(org_id=self.org2_id, name="Security")
        self.db.add_all([r1, r2, r3])
        self.db.commit()

        self.role_org1_ids = [r1.id, r2.id]
        self.role_org2_id = r3.id

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    # ---- get_jobroles ----
    def test_get_jobroles_all_for_org(self):
        rows = service.get_jobroles(self.db, org_id=self.org1_id)
        names = {r.name for r in rows}
        self.assertEqual(names, {"Nurse", "Receptionist"})

    # ---- get_jobrole ----
    def test_get_jobrole_found(self):
        target = self.role_org1_ids[0]
        got = service.get_jobrole(self.db, target)
        self.assertIsNotNone(got)
        self.assertEqual(got.id, target)

    def test_get_jobrole_not_found(self):
        got = service.get_jobrole(self.db, 999999)
        self.assertIsNone(got)

    # ---- get_jobrole_for_org ----
    def test_get_jobrole_for_org_ok(self):
        target = self.role_org1_ids[0]
        row = service.get_jobrole_for_org(self.db, target, self.org1_id)
        self.assertIsNotNone(row)
        self.assertEqual(row.id, target)
        self.assertEqual(row.org_id, self.org1_id)

    def test_get_jobrole_for_org_mismatch(self):
        target = self.role_org1_ids[0]
        row = service.get_jobrole_for_org(self.db, target, self.org2_id)
        self.assertIsNone(row)

    # ---- create_jobrole ----
    def test_create_jobrole_inserts_and_returns(self):
        payload = JobRoleCreate(org_id=self.org1_id, name="Pharmacist")
        created = service.create_jobrole(self.db, payload)
        self.assertIsInstance(created.id, int)
        self.assertEqual(created.name, "Pharmacist")
        again = service.get_jobrole(self.db, created.id)
        self.assertIsNotNone(again)
        self.assertEqual(again.name, "Pharmacist")

    # ---- update_jobrole ----
    def test_update_jobrole_name_only(self):
        target = self.role_org1_ids[0]
        updated = service.update_jobrole(self.db, target, JobRoleUpdate(name="Senior Nurse"))
        self.assertIsNotNone(updated)
        self.assertEqual(updated.name, "Senior Nurse")
        self.assertEqual(updated.org_id, self.org1_id)

    # ---- delete_jobrole ----
    def test_delete_jobrole(self):
        target = self.role_org1_ids[1]
        row = self.db.get(JobRole, target)
        self.assertIsNotNone(row)
        service.delete_jobrole(self.db, target)
        self.assertIsNone(self.db.get(JobRole, target))


if __name__ == "__main__":
    unittest.main()
