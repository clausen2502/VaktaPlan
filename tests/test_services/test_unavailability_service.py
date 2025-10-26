# tests/test_services/test_unavailability_service.py
import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.database import Base
from sqlalchemy.orm import Session

from organization.models import Organization
from employee.models import Employee
from unavailability.models import Unavailability
from unavailability import service
from unavailability.schema import UnavailabilityCreate, UnavailabilityUpdate
from fastapi import HTTPException



class UnavailabilityServiceTests(unittest.TestCase):
    def setUp(self):
        # Fresh in-memory DB
        self.engine = create_engine("sqlite:///:memory:", future=True)
        Base.metadata.create_all(self.engine)

        TestingSession = sessionmaker(bind=self.engine, future=True)
        self.db: Session = TestingSession()

        # --- seed orgs ---
        org1 = Organization(name="Org One", timezone="Atlantic/Reykjavik")
        org2 = Organization(name="Org Two", timezone="Atlantic/Reykjavik")
        self.db.add_all([org1, org2])
        self.db.flush()
        self.org1_id = org1.id
        self.org2_id = org2.id

        # --- seed employees ---
        e1 = Employee(org_id=self.org1_id, display_name="Kalli")
        e2 = Employee(org_id=self.org1_id, display_name="Palli")
        e3 = Employee(org_id=self.org2_id, display_name="Alli")
        self.db.add_all([e1, e2, e3])
        self.db.flush()
        self.emp1_id = e1.id   # org1
        self.emp2_id = e2.id   # org1
        self.emp3_id = e3.id   # org2

        # --- seed unavailability rows ---
        now = datetime(2025, 10, 1, 9, 0)
        ua1 = Unavailability(  # org1/e1
            employee_id=self.emp1_id,
            start_at=now,
            end_at=now + timedelta(hours=2),
            reason="dentist",
        )
        ua2 = Unavailability(  # org1/e2
            employee_id=self.emp2_id,
            start_at=now + timedelta(days=1),
            end_at=now + timedelta(days=1, hours=3),
            reason="errand",
        )
        ua3 = Unavailability(  # org2/e3
            employee_id=self.emp3_id,
            start_at=now + timedelta(days=2),
            end_at=now + timedelta(days=2, hours=1),
            reason="offsite",
        )
        self.db.add_all([ua1, ua2, ua3])
        self.db.commit()
        self.db.refresh(ua1)
        self.db.refresh(ua2)
        self.db.refresh(ua3)
        self.ua1_id = ua1.id
        self.ua2_id = ua2.id
        self.ua3_id = ua3.id

        self.now = now

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    # ---- get_unavailability (by id) ----

    def test_get_unavailability_found(self):
        row = service.get_unavailability(self.db, self.ua1_id)
        self.assertIsNotNone(row)
        self.assertEqual(row.id, self.ua1_id)

    def test_get_unavailability_not_found(self):
        row = service.get_unavailability(self.db, 999999)
        self.assertIsNone(row)

    # ---- get_unavailability_for_org ----

    def test_get_unavailability_for_org_ok(self):
        row = service.get_unavailability_for_org(self.db, self.ua1_id, self.org1_id)
        self.assertIsNotNone(row)
        self.assertEqual(row.employee_id, self.emp1_id)

    def test_get_unavailability_for_org_mismatch(self):
        # ua1 belongs to org1; ask for org2 -> None
        row = service.get_unavailability_for_org(self.db, self.ua1_id, self.org2_id)
        self.assertIsNone(row)

    # ---- get_unavailabilities (list) ----

    def test_get_unavailabilities_for_org(self):
        rows = service.get_unavailabilities(self.db, org_id=self.org1_id)
        # should not include org2's row
        ids = {r.id for r in rows}
        self.assertTrue(self.ua1_id in ids and self.ua2_id in ids)
        self.assertFalse(self.ua3_id in ids)

    def test_get_unavailabilities_filter_by_employee(self):
        rows = service.get_unavailabilities(self.db, org_id=self.org1_id, employee_id=self.emp1_id)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].employee_id, self.emp1_id)

    # ---- create_unavailability ----

    def test_create_unavailability_inserts_and_returns(self):
        dto = UnavailabilityCreate(
            org_id=self.org1_id,
            employee_id=self.emp1_id,
            start_at=self.now + timedelta(days=3, hours=8),
            end_at=self.now + timedelta(days=3, hours=12),
            reason="family",
        )
        created = service.create_unavailability(self.db, dto)
        self.assertIsInstance(created.id, int)

        fetched = service.get_unavailability(self.db, created.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.reason, "family")
        self.assertEqual(fetched.employee_id, self.emp1_id)

    def test_create_unavailability_cross_org_forbidden(self):
        # Try to create for employee in org2 while claiming org1
        dto = UnavailabilityCreate(
            org_id=self.org1_id,
            employee_id=self.emp3_id,  # belongs to org2
            start_at=self.now + timedelta(days=4),
            end_at=self.now + timedelta(days=4, hours=1),
            reason=None,
        )
        with self.assertRaises(HTTPException) as ctx:
            service.create_unavailability(self.db, dto)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_create_unavailability_window_validation(self):
        dto = UnavailabilityCreate(
            org_id=self.org1_id,
            employee_id=self.emp1_id,
            start_at=self.now + timedelta(hours=4),
            end_at=self.now + timedelta(hours=2),
            reason="bad window",
        )
        with self.assertRaises(HTTPException) as ctx:
            service.create_unavailability(self.db, dto)
        self.assertEqual(ctx.exception.status_code, 422)

    # ---- update_unavailability ----

    def test_update_unavailability_ok(self):
        patch = UnavailabilityUpdate(
            start_at=self.now + timedelta(hours=1),
            end_at=self.now + timedelta(hours=3),
            reason="moved",
        )
        updated = service.update_unavailability(self.db, self.ua1_id, patch, org_id=self.org1_id)
        self.assertIsNotNone(updated)
        self.assertEqual(updated.reason, "moved")
        self.assertEqual(updated.start_at, self.now + timedelta(hours=1))
        self.assertEqual(updated.end_at, self.now + timedelta(hours=3))

    def test_update_unavailability_not_found_returns_none(self):
        patch = UnavailabilityUpdate(reason="noop")
        res = service.update_unavailability(self.db, 999999, patch, org_id=self.org1_id)
        self.assertIsNone(res)

    def test_update_unavailability_window_validation(self):
        patch = UnavailabilityUpdate(end_at=self.now - timedelta(hours=1))
        with self.assertRaises(HTTPException) as ctx:
            service.update_unavailability(self.db, self.ua1_id, patch, org_id=self.org1_id)
        self.assertEqual(ctx.exception.status_code, 422)


    # ---- delete_unavailability ----

    def test_delete_unavailability_true_when_deleted(self):
        ok = service.delete_unavailability(self.db, self.ua2_id, org_id=self.org1_id)
        self.assertTrue(ok)
        self.assertIsNone(service.get_unavailability(self.db, self.ua2_id))

    def test_delete_unavailability_false_when_missing(self):
        ok = service.delete_unavailability(self.db, 999999, org_id=self.org1_id)
        self.assertFalse(ok)

    def test_delete_unavailability_wrong_org_false(self):
        # ua1 is org1; try to delete as org2
        ok = service.delete_unavailability(self.db, self.ua1_id, org_id=self.org2_id)
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
