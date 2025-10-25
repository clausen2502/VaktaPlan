import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.database import Base
from sqlalchemy.orm import Session
from organization.models import Organization
from employee.models import Employee
from employee import service
from employee.schema import EmployeeCreate, EmployeeUpdate


class Obj:
    """Simple attribute container for payload mocks."""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class employeeServiceTests(unittest.TestCase):
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

        # --- seed employees ---
        l1 = Employee(org_id=self.org1_id, display_name="Kalli")
        l2 = Employee(org_id=self.org1_id, display_name="Palli")
        l3 = Employee(org_id=self.org2_id, display_name="Alli")
        self.db.add_all([l1, l2, l3])
        self.db.commit()
        self.db.refresh(l1); self.db.refresh(l2); self.db.refresh(l3)

        self.loc_org1_ids = [l1.id, l2.id]
        self.loc_org2_id = l3.id

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    # ---- get_employee ----
    def test_get_employee_found(self):
        got = service.get_employee(self.db, self.loc_org1_ids[0])
        self.assertIsNotNone(got)
        self.assertEqual(got.id, self.loc_org1_ids[0])

    def test_get_employee_not_found(self):
        got = service.get_employee(self.db, 999999)
        self.assertIsNone(got)

    # ---- get_employees ----

    def test_get_employees_all_for_org(self):
        rows = service.get_employees(self.db, org_id=self.org1_id)
        display_names = {r.display_name for r in rows}
        self.assertEqual(display_names, {"Kalli", "Palli"})


    # ---- get_employee_for_org ----
    def test_get_employee_for_org_ok(self):
        target = self.loc_org1_ids[0]
        row = service.get_employee_for_org(self.db, target, self.org1_id)
        self.assertIsNotNone(row)
        self.assertEqual(row.id, target)
        self.assertEqual(row.org_id, self.org1_id)

    def test_get_employee_for_org_mismatch(self):
        target = self.loc_org1_ids[0]  # belongs to org1
        row = service.get_employee_for_org(self.db, target, self.org2_id)
        self.assertIsNone(row)

    # ---- create_employee ----
    def test_create_employee_inserts_and_returns(self):
        # use the internal DTO that the router would build
        payload = EmployeeCreate(org_id=self.org1_id, display_name="Jonas")

        created = service.create_employee(self.db, payload)
        self.assertIsInstance(created.id, int)

        again = service.get_employee(self.db, created.id)
        self.assertIsNotNone(again)
        self.assertEqual(again.display_name, "Jonas")

    # ---- update_employee ----
    def test_update_employee_display_name_only(self):
        target = self.loc_org1_ids[0]
        updated = service.update_employee(self.db, target, EmployeeUpdate(display_name="Kalli"))
        self.assertIsNotNone(updated)
        self.assertEqual(updated.display_name, "Kalli")
        # org_id should remain unchanged
        self.assertEqual(updated.org_id, self.org1_id)

    def test_update_employee_not_found_returns_none(self):
        res = service.update_employee(self.db, 999999, EmployeeUpdate(display_name="X"))
        self.assertIsNone(res)

    # ---- delete_employee ----
    def delete_employee(db: Session, loc_id: int) -> bool:
        row = db.get(Employee, loc_id)
        if not row:
            return False
        db.delete(row)
        db.commit()
        return True


if __name__ == "__main__":
    unittest.main()
