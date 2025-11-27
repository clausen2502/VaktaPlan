import unittest
from datetime import datetime, timedelta, timezone, date, time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.database import Base

from user.models import User
from organization.models import Organization
from location.models import Location
from jobrole.models import JobRole
from employee.models import Employee
from schedule.models import Schedule, ScheduleStatus
from shift.models import Shift
from assignment.models import Assignment
from unavailability.models import Unavailability
from preference.models import Preference

from assignment.auto_assign_service import auto_assign


class AutoAssignServiceTests(unittest.TestCase):
    def setUp(self):
        # fresh in-memory DB for each test
        self.engine = create_engine("sqlite:///:memory:", future=True)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine, future=True)
        self.db = Session()

        # --- org, location, role, schedule ---

        self.org = Organization(name="Org", timezone="Atlantic/Reykjavik")
        self.db.add(self.org)
        self.db.flush()

        self.location = Location(org_id=self.org.id, name="Store")
        self.db.add(self.location)
        self.db.flush()

        # default: no weekly cap, tests can override
        self.role = JobRole(
            org_id=self.org.id,
            name="Cashier",
            weekly_hours_cap=None,
        )
        self.db.add(self.role)
        self.db.flush()

        self.schedule = Schedule(
            org_id=self.org.id,
            range_start=date(2025, 1, 1),
            range_end=date(2025, 1, 7),
            version=1,
            status=ScheduleStatus.draft,
            created_by=None,
            published_at=None,
        )
        self.db.add(self.schedule)
        self.db.flush()

        # one base employee; tests can add more
        self.emp1 = Employee(org_id=self.org.id, display_name="Emp1")
        self.db.add(self.emp1)
        self.db.flush()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    # -------------------------------------------------
    # 1) One shift, required_staff_count=2, 3 employees
    # -------------------------------------------------
    def test_auto_assign_fills_required_staff_for_shift(self):
        base_time = datetime(2025, 1, 2, 9, 0, tzinfo=timezone.utc)

        shift = Shift(
            org_id=self.org.id,
            schedule_id=self.schedule.id,
            location_id=self.location.id,
            role_id=self.role.id,
            start_at=base_time,
            end_at=base_time + timedelta(hours=8),
            required_staff_count=2,
            notes=None,
        )
        self.db.add(shift)

        # add two extra employees so we have 3 total
        emp2 = Employee(org_id=self.org.id, display_name="Emp2")
        emp3 = Employee(org_id=self.org.id, display_name="Emp3")
        self.db.add_all([emp2, emp3])
        self.db.commit()

        result = auto_assign(
            db=self.db,
            schedule_id=self.schedule.id,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 7),
            policy="fill_missing",
            dry_run=False,
        )

        self.assertEqual(result["assigned"], 2)

        rows = self.db.query(Assignment).all()
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r.shift_id == shift.id for r in rows))

    # -------------------------------------------------
    # 2) Weekly cap: one employee, two 8h shifts, cap=8
    # -------------------------------------------------
    def test_auto_assign_respects_weekly_role_cap(self):
        # only emp1 is in DB (from setUp)
        # set weekly cap to 8 hours
        self.role.weekly_hours_cap = 8
        self.db.commit()

        monday = datetime(2025, 1, 6, 9, 0, tzinfo=timezone.utc)  # Monday
        tuesday = monday + timedelta(days=1)

        # two 8h shifts in same ISO week
        shift1 = Shift(
            org_id=self.org.id,
            schedule_id=self.schedule.id,
            location_id=self.location.id,
            role_id=self.role.id,
            start_at=monday,
            end_at=monday + timedelta(hours=8),
            required_staff_count=1,
            notes=None,
        )
        shift2 = Shift(
            org_id=self.org.id,
            schedule_id=self.schedule.id,
            location_id=self.location.id,
            role_id=self.role.id,
            start_at=tuesday,
            end_at=tuesday + timedelta(hours=8),
            required_staff_count=1,
            notes=None,
        )
        self.db.add_all([shift1, shift2])
        self.db.commit()

        result = auto_assign(
            db=self.db,
            schedule_id=self.schedule.id,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 7),
            policy="fill_missing",
            dry_run=False,
        )

        # Only one of the two shifts should be filled, because cap=8h
        self.assertEqual(result["assigned"], 1)

        assigned_rows = self.db.query(Assignment).all()
        self.assertEqual(len(assigned_rows), 1)
        self.assertIn(
            assigned_rows[0].shift_id,
            {shift1.id, shift2.id},
        )
        self.assertEqual(assigned_rows[0].employee_id, self.emp1.id)

    # -------------------------------------------------
    # 3) dry_run: we still get 'assigned' count, but DB unchanged
    # -------------------------------------------------
    def test_auto_assign_dry_run_creates_no_assignments(self):
        base_time = datetime(2025, 1, 2, 9, 0, tzinfo=timezone.utc)

        shift = Shift(
            org_id=self.org.id,
            schedule_id=self.schedule.id,
            location_id=self.location.id,
            role_id=self.role.id,
            start_at=base_time,
            end_at=base_time + timedelta(hours=8),
            required_staff_count=2,
            notes=None,
        )
        self.db.add(shift)

        # add two extra employees so we have 3 total
        emp2 = Employee(org_id=self.org.id, display_name="Emp2")
        emp3 = Employee(org_id=self.org.id, display_name="Emp3")
        self.db.add_all([emp2, emp3])
        self.db.commit()

        result = auto_assign(
            db=self.db,
            schedule_id=self.schedule.id,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 7),
            policy="fill_missing",
            dry_run=True,
        )

        # Logic still "assigns" 2 in memory
        self.assertEqual(result["assigned"], 2)

        # But nothing is written to DB
        rows = self.db.query(Assignment).all()
        self.assertEqual(len(rows), 0)

    # -------------------------------------------------
    # 4) Unavailability: employee with overlapping unavailability
    #    must never be assigned to that shift.
    # -------------------------------------------------
    def test_auto_assign_respects_unavailability(self):
        base_time = datetime(2025, 1, 3, 9, 0, tzinfo=timezone.utc)

        shift = Shift(
            org_id=self.org.id,
            schedule_id=self.schedule.id,
            location_id=self.location.id,
            role_id=self.role.id,
            start_at=base_time,
            end_at=base_time + timedelta(hours=8),
            required_staff_count=1,
            notes=None,
        )
        self.db.add(shift)

        # Second employee who is available
        emp2 = Employee(org_id=self.org.id, display_name="Emp2")
        self.db.add(emp2)
        self.db.flush()

        # emp1 is unavailable for the entire shift
        unavail = Unavailability(
            employee_id=self.emp1.id,
            start_at=base_time,
            end_at=base_time + timedelta(hours=8),
        )
        self.db.add(unavail)
        self.db.commit()

        result = auto_assign(
            db=self.db,
            schedule_id=self.schedule.id,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 7),
            policy="fill_missing",
            dry_run=False,
        )

        self.assertEqual(result["assigned"], 1)

        rows = self.db.query(Assignment).all()
        self.assertEqual(len(rows), 1)
        # Must have assigned the available employee, not the unavailable one
        self.assertEqual(rows[0].employee_id, emp2.id)

    # -------------------------------------------------
    # 5) Preferences: highest weight on overlapping pref wins.
    # -------------------------------------------------
    def test_auto_assign_pref_picks_highest_weight(self):
        base_time = datetime(2025, 1, 2, 10, 0, tzinfo=timezone.utc)

        shift = Shift(
            org_id=self.org.id,
            schedule_id=self.schedule.id,
            location_id=self.location.id,
            role_id=self.role.id,
            start_at=base_time,
            end_at=base_time + timedelta(hours=4),
            required_staff_count=1,
            notes=None,
        )
        self.db.add(shift)

        # Two more employees
        emp2 = Employee(org_id=self.org.id, display_name="Emp2")
        emp3 = Employee(org_id=self.org.id, display_name="Emp3")
        self.db.add_all([emp2, emp3])
        self.db.flush()

        weekday = base_time.weekday()  # match shift weekday

        # emp1: low weight preference
        pref1 = Preference(
            employee_id=self.emp1.id,
            weekday=weekday,
            start_time=time(9, 0),
            end_time=time(18, 0),
            weight=1,
            do_not_schedule=False,
        )

        # emp2: higher weight preference, should win
        pref2 = Preference(
            employee_id=emp2.id,
            weekday=weekday,
            start_time=time(9, 0),
            end_time=time(18, 0),
            weight=5,
            do_not_schedule=False,
        )

        # emp3: no preference at all (weight=0 implied)
        self.db.add_all([pref1, pref2])
        self.db.commit()

        result = auto_assign(
            db=self.db,
            schedule_id=self.schedule.id,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 7),
            policy="fill_missing",
            dry_run=False,
        )

        self.assertEqual(result["assigned"], 1)

        rows = self.db.query(Assignment).all()
        self.assertEqual(len(rows), 1)
        # The higher-weight employee should be chosen
        self.assertEqual(rows[0].employee_id, emp2.id)

    # -------------------------------------------------
    # 6) Existing assignments + fill_missing:
    #    required_staff_count=3, one already assigned,
    #    auto_assign should add only 2 more.
    # -------------------------------------------------
    def test_auto_assign_respects_existing_assignments_fill_missing(self):
        base_time = datetime(2025, 1, 4, 9, 0, tzinfo=timezone.utc)

        shift = Shift(
            org_id=self.org.id,
            schedule_id=self.schedule.id,
            location_id=self.location.id,
            role_id=self.role.id,
            start_at=base_time,
            end_at=base_time + timedelta(hours=8),
            required_staff_count=3,
            notes=None,
        )
        self.db.add(shift)
        self.db.flush()

        # Already one assignment for this shift (emp1)
        existing = Assignment(
            shift_id=shift.id,
            employee_id=self.emp1.id,
        )
        self.db.add(existing)

        # Two more employees that can fill remaining seats
        emp2 = Employee(org_id=self.org.id, display_name="Emp2")
        emp3 = Employee(org_id=self.org.id, display_name="Emp3")
        self.db.add_all([emp2, emp3])
        self.db.commit()

        result = auto_assign(
            db=self.db,
            schedule_id=self.schedule.id,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 7),
            policy="fill_missing",
            dry_run=False,
        )

        # Only 2 NEW seats should be auto-assigned
        self.assertEqual(result["assigned"], 2)

        rows = self.db.query(Assignment).filter(Assignment.shift_id == shift.id).all()
        self.assertEqual(len(rows), 3)  # 1 existing + 2 new

        emp_ids = {r.employee_id for r in rows}
        self.assertEqual(emp_ids, {self.emp1.id, emp2.id, emp3.id})

    # -------------------------------------------------
    # 7) No candidates:
    #    all employees have do_not_schedule=True for that window,
    #    so auto_assign should not assign anyone and bump skipped_no_candidates.
    # -------------------------------------------------
    def test_auto_assign_no_candidates_skipped_no_candidates_incremented(self):
        base_time = datetime(2025, 1, 5, 9, 0, tzinfo=timezone.utc)

        shift = Shift(
            org_id=self.org.id,
            schedule_id=self.schedule.id,
            location_id=self.location.id,
            role_id=self.role.id,
            start_at=base_time,
            end_at=base_time + timedelta(hours=8),
            required_staff_count=1,
            notes=None,
        )
        self.db.add(shift)

        # Another employee, both will have do_not_schedule prefs
        emp2 = Employee(org_id=self.org.id, display_name="Emp2")
        self.db.add(emp2)
        self.db.flush()

        weekday = base_time.weekday()

        # emp1: do_not_schedule overlapping
        p1 = Preference(
            employee_id=self.emp1.id,
            weekday=weekday,
            start_time=time(8, 0),
            end_time=time(18, 0),
            do_not_schedule=True,
            weight=0,
        )
        # emp2: also blocked
        p2 = Preference(
            employee_id=emp2.id,
            weekday=weekday,
            start_time=time(8, 0),
            end_time=time(18, 0),
            do_not_schedule=True,
            weight=0,
        )

        self.db.add_all([p1, p2])
        self.db.commit()

        result = auto_assign(
            db=self.db,
            schedule_id=self.schedule.id,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 7),
            policy="fill_missing",
            dry_run=False,
        )

        self.assertEqual(result["assigned"], 0)
        self.assertEqual(result["skipped_no_candidates"], 1)

        rows = self.db.query(Assignment).all()
        self.assertEqual(len(rows), 0)

    # -------------------------------------------------
    # 8) reassign_all: old (invalid) assignment is removed,
    #    new valid one is created
    # -------------------------------------------------
    def test_auto_assign_reassign_all_replaces_existing_assignments(self):
        base_time = datetime(2025, 1, 3, 9, 0, tzinfo=timezone.utc)

        # One shift needing 1 staff
        shift = Shift(
            org_id=self.org.id,
            schedule_id=self.schedule.id,
            location_id=self.location.id,
            role_id=self.role.id,
            start_at=base_time,
            end_at=base_time + timedelta(hours=8),
            required_staff_count=1,
            notes=None,
        )
        self.db.add(shift)

        # Second employee
        emp2 = Employee(org_id=self.org.id, display_name="Emp2")
        self.db.add(emp2)
        self.db.flush()

        # Make Emp1 unavailable for this shift, so they should never be picked
        from unavailability.models import Unavailability

        unavail = Unavailability(
            employee_id=self.emp1.id,
            start_at=base_time,
            end_at=base_time + timedelta(hours=8),
            reason="Busy",
        )
        self.db.add(unavail)

        # Old assignment: Emp1 is assigned even though they shouldn't be
        old_assignment = Assignment(
            shift_id=shift.id,
            employee_id=self.emp1.id,
        )
        self.db.add(old_assignment)
        self.db.commit()

        # Sanity check before
        before_rows = self.db.query(Assignment).all()
        self.assertEqual(len(before_rows), 1)
        self.assertEqual(before_rows[0].employee_id, self.emp1.id)

        # Run auto_assign with reassign_all → should drop Emp1 and pick Emp2
        result = auto_assign(
            db=self.db,
            schedule_id=self.schedule.id,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 7),
            policy="reassign_all",
            dry_run=False,
        )

        self.assertEqual(result["policy"], "reassign_all")
        self.assertEqual(result["assigned"], 1)

        after_rows = self.db.query(Assignment).all()
        self.assertEqual(len(after_rows), 1)
        self.assertEqual(after_rows[0].shift_id, shift.id)
        # Now Emp2 should be assigned (Emp1 is blocked by unavailability)
        self.assertEqual(after_rows[0].employee_id, emp2.id)

    # -------------------------------------------------
    # 9) reassign_all + dry_run=True: existing assignments
    #    stay untouched, nothing is deleted
    # -------------------------------------------------
    def test_auto_assign_reassign_all_dry_run_does_not_modify_db(self):
        base_time = datetime(2025, 1, 4, 9, 0, tzinfo=timezone.utc)

        shift = Shift(
            org_id=self.org.id,
            schedule_id=self.schedule.id,
            location_id=self.location.id,
            role_id=self.role.id,
            start_at=base_time,
            end_at=base_time + timedelta(hours=8),
            required_staff_count=1,
            notes=None,
        )
        self.db.add(shift)
        self.db.flush()

        # Existing assignment for Emp1
        existing = Assignment(
            shift_id=shift.id,
            employee_id=self.emp1.id,
        )
        self.db.add(existing)
        self.db.commit()

        count_before = self.db.query(Assignment).count()
        rows_before = self.db.query(Assignment).all()
        self.assertEqual(count_before, 1)
        self.assertEqual(rows_before[0].employee_id, self.emp1.id)

        result = auto_assign(
            db=self.db,
            schedule_id=self.schedule.id,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 7),
            policy="reassign_all",
            dry_run=True,
        )

        # dry_run: no deletes, no inserts
        count_after = self.db.query(Assignment).count()
        rows_after = self.db.query(Assignment).all()

        self.assertEqual(result["policy"], "reassign_all")
        # Shift is already full, so auto_assign will not "assign" anything
        self.assertEqual(result["assigned"], 0)

        self.assertEqual(count_after, count_before)
        self.assertEqual(len(rows_after), 1)
        self.assertEqual(rows_after[0].shift_id, shift.id)
        self.assertEqual(rows_after[0].employee_id, self.emp1.id)


if __name__ == "__main__":
    unittest.main()
