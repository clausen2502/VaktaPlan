import unittest
from datetime import datetime, timedelta, timezone, date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.database import Base

from fastapi import HTTPException
from organization.models import Organization
from location.models import Location
from jobrole.models import JobRole
from employee.models import Employee
from shift.models import Shift
from assignment.models import Assignment
from schedule.models import Schedule, ScheduleStatus

# Service + DTOs under test
from assignment import service
from assignment.schema import AssignmentCreate, AssignmentUpdate


class AssignmentServiceTests(unittest.TestCase):
    def setUp(self):
        # Fresh in-memory DB
        self.engine = create_engine("sqlite:///:memory:", future=True)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine, future=True)
        self.db = Session()

        # ---- Seed orgs ----
        self.org1 = Organization(name="Org One", timezone="Atlantic/Reykjavik")
        self.org2 = Organization(name="Org Two", timezone="Atlantic/Reykjavik")
        self.db.add_all([self.org1, self.org2])
        self.db.flush()

        # ---- Seed locations + roles (for Shift FKs) ----
        self.loc1 = Location(org_id=self.org1.id, name="HQ1")
        self.loc2 = Location(org_id=self.org2.id, name="HQ2")
        self.role1 = JobRole(org_id=self.org1.id, name="Cashier")
        self.role2 = JobRole(org_id=self.org2.id, name="Cook")
        self.db.add_all([self.loc1, self.loc2, self.role1, self.role2])
        self.db.flush()

        # ---- Seed employees ----
        self.emp1_o1 = Employee(org_id=self.org1.id, display_name="Kalli")
        self.emp2_o1 = Employee(org_id=self.org1.id, display_name="Palli")
        self.emp1_o2 = Employee(org_id=self.org2.id, display_name="Alli")
        self.db.add_all([self.emp1_o1, self.emp2_o1, self.emp1_o2])
        self.db.flush()

        # ---- Seed schedules (required by Shift FK) ----
        sched1 = Schedule(
            org_id=self.org1.id,
            range_start=date(2025, 10, 1),
            range_end=date(2025, 10, 31),
            version=1,
            status=ScheduleStatus.draft,
            created_by=None,
            published_at=None,
        )
        sched2 = Schedule(
            org_id=self.org2.id,
            range_start=date(2025, 10, 1),
            range_end=date(2025, 10, 31),
            version=1,
            status=ScheduleStatus.draft,
            created_by=None,
            published_at=None,
        )
        self.db.add_all([sched1, sched2])
        self.db.flush()
        self.schedule1_id = sched1.id
        self.schedule2_id = sched2.id

        # ---- Seed shifts ----
        now = datetime(2025, 10, 1, 9, 0, tzinfo=timezone.utc)
        self.sh1_o1 = Shift(
            org_id=self.org1.id,
            schedule_id=self.schedule1_id,
            location_id=self.loc1.id,
            role_id=self.role1.id,
            start_at=now,
            end_at=now + timedelta(hours=8),
            notes=None,
        )
        self.sh2_o1 = Shift(
            org_id=self.org1.id,
            schedule_id=self.schedule1_id,
            location_id=self.loc1.id,
            role_id=self.role1.id,
            start_at=now + timedelta(days=1),
            end_at=now + timedelta(days=1, hours=8),
            notes=None,
        )
        self.sh1_o2 = Shift(
            org_id=self.org2.id,
            schedule_id=self.schedule2_id,
            location_id=self.loc2.id,
            role_id=self.role2.id,
            start_at=now,
            end_at=now + timedelta(hours=6),
            notes=None,
        )
        self.db.add_all([self.sh1_o1, self.sh2_o1, self.sh1_o2])
        self.db.flush()

        # ---- Seed one assignment in org1 ----
        self.a1 = Assignment(
            shift_id=self.sh1_o1.id,
            employee_id=self.emp1_o1.id,
        )
        self.db.add(self.a1)
        self.db.commit()

        self.org1_id = self.org1.id
        self.org2_id = self.org2.id

    def tearDown(self):
        self.db.close()
        self.engine.dispose()


    # -------------- LIST ----------------

    def test_get_assignments_all_for_org(self):
        rows = service.get_assignments(self.db, org_id=self.org1_id)
        got = {(r.shift_id, r.employee_id) for r in rows}
        self.assertIn((self.sh1_o1.id, self.emp1_o1.id), got)
        # Ensure nothing from org2 leaks in
        got2 = service.get_assignments(self.db, org_id=self.org2_id)
        for r in got2:
            self.assertEqual(r.shift.org_id, self.org2_id)

    def test_get_assignments_filter_by_shift(self):
        rows = service.get_assignments(self.db, org_id=self.org1_id, shift_id=self.sh1_o1.id)
        self.assertTrue(all(r.shift_id == self.sh1_o1.id for r in rows))

    def test_get_assignments_filter_by_employee(self):
        rows = service.get_assignments(self.db, org_id=self.org1_id, employee_id=self.emp1_o1.id)
        self.assertTrue(all(r.employee_id == self.emp1_o1.id for r in rows))

    # -------------- GET (single) ----------------

    def test_get_assignment_for_org_ok(self):
        row = service.get_assignment_for_org(
            self.db, self.sh1_o1.id, self.emp1_o1.id, org_id=self.org1_id
        )
        self.assertIsNotNone(row)
        self.assertEqual(row.shift_id, self.sh1_o1.id)
        self.assertEqual(row.employee_id, self.emp1_o1.id)

    def test_get_assignment_for_org_none_wrong_org(self):
        # Assignment belongs to org1, querying with org2 should return None
        row = service.get_assignment_for_org(
            self.db, self.sh1_o1.id, self.emp1_o1.id, org_id=self.org2_id
        )
        self.assertIsNone(row)

    # -------------- CREATE ----------------

    def test_create_assignment_inserts_and_returns(self):
        dto = AssignmentCreate(
            org_id=self.org1_id,
            shift_id=self.sh2_o1.id,
            employee_id=self.emp2_o1.id,
        )
        created = service.create_assignment(self.db, dto)
        self.assertEqual(created.shift_id, self.sh2_o1.id)
        self.assertEqual(created.employee_id, self.emp2_o1.id)

    def test_create_assignment_404_if_shift_wrong_org(self):
        # shift from org2 with org1 payload => 404

        dto = AssignmentCreate(
            org_id=self.org1_id,
            shift_id=self.sh1_o2.id,
            employee_id=self.emp1_o1.id,
        )
        with self.assertRaises(HTTPException) as cm:
            service.create_assignment(self.db, dto)
        self.assertEqual(cm.exception.status_code, 404)
        self.assertEqual(cm.exception.detail, "shift not found")

    def test_create_assignment_404_if_employee_wrong_org(self):
        # employee from org2 with org1 payload => 404
        dto = AssignmentCreate(
            org_id=self.org1_id,
            shift_id=self.sh1_o1.id,        # org1
            employee_id=self.emp1_o2.id,    # belongs to org2
        )
        with self.assertRaises(HTTPException) as cm:
            service.create_assignment(self.db, dto)
        self.assertEqual(cm.exception.status_code, 404)
        self.assertEqual(cm.exception.detail, "employee not found")

    def test_create_assignment_duplicate_raises_integrity_error(self):
        # Composite PK duplicate should raise IntegrityError on commit
        from sqlalchemy.exc import IntegrityError

        dto = AssignmentCreate(
            org_id=self.org1_id,
            shift_id=self.sh1_o1.id,
            employee_id=self.emp1_o1.id,   # already assigned in setUp
        )
        with self.assertRaises(IntegrityError):
            service.create_assignment(self.db, dto)

    # -------------- UPDATE ----------------

    def test_update_assignment_404_when_missing_or_wrong_org(self):
        from fastapi import HTTPException

        patch = AssignmentUpdate()
        # wrong org
        with self.assertRaises(HTTPException) as cm:
            service.update_assignment(
                self.db, self.sh1_o1.id, self.emp1_o1.id, patch, org_id=self.org2_id
            )
        self.assertEqual(cm.exception.status_code, 404)
        self.assertEqual(cm.exception.detail, "assignment not found")

        # non-existent composite key
        with self.assertRaises(HTTPException) as cm2:
            service.update_assignment(
                self.db, 999999, 999999, patch, org_id=self.org1_id
            )
        self.assertEqual(cm2.exception.status_code, 404)
        self.assertEqual(cm2.exception.detail, "assignment not found")

    # -------------- DELETE ----------------

    def test_delete_assignment_true_when_deleted(self):
        ok = service.delete_assignment(self.db, self.sh1_o1.id, self.emp1_o1.id)
        self.assertIsNone(ok)  # function returns None, but we can verify it’s gone
        still = self.db.get(Assignment, (self.sh1_o1.id, self.emp1_o1.id))
        self.assertIsNone(still)

    def test_delete_assignment_false_when_missing_is_ok(self):
        # delete is idempotent; returns None either way
        res = service.delete_assignment(self.db, 999999, 888888)
        self.assertIsNone(res)


if __name__ == "__main__":
    unittest.main()
