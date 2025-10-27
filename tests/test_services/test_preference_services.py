import unittest
from datetime import date, time, timezone, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fastapi import HTTPException

from core.database import Base
from organization.models import Organization
from location.models import Location
from jobrole.models import JobRole
from employee.models import Employee
from preference.models import Preference
from preference import service
from preference.schema import PreferenceCreate, PreferenceUpdate


class PreferenceServiceTests(unittest.TestCase):
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
        self.org1_id, self.org2_id = self.org1.id, self.org2.id

        # ---- Seed locations + roles ----
        self.loc1 = Location(org_id=self.org1_id, name="HQ1")
        self.loc2 = Location(org_id=self.org2_id, name="HQ2")
        self.role1 = JobRole(org_id=self.org1_id, name="Cashier")
        self.role2 = JobRole(org_id=self.org2_id, name="Cook")
        self.db.add_all([self.loc1, self.loc2, self.role1, self.role2])
        self.db.flush()

        # ---- Seed employees ----
        self.emp1_o1 = Employee(org_id=self.org1_id, display_name="Kalli")
        self.emp2_o1 = Employee(org_id=self.org1_id, display_name="Palli")
        self.emp1_o2 = Employee(org_id=self.org2_id, display_name="Alli")
        self.db.add_all([self.emp1_o1, self.emp2_o1, self.emp1_o2])
        self.db.flush()

        # ---- Seed preferences in org1 (plus one in org2) ----
        # Mon 09:00-12:00 (role1, loc1)
        p1 = Preference(
            employee_id=self.emp1_o1.id,
            weekday=1,  # Monday (0=Sun if you use that; tests don't assume mapping)
            start_time=time(9, 0),
            end_time=time(12, 0),
            role_id=self.role1.id,
            location_id=self.loc1.id,
            weight=5,
            do_not_schedule=False,
            notes="Morning",
            active_start=date(2025, 10, 1),
            active_end=date(2025, 10, 31),
        )
        # Wed any time (no times set), only location filter
        p2 = Preference(
            employee_id=self.emp1_o1.id,
            weekday=3,
            start_time=None,
            end_time=None,
            role_id=None,
            location_id=self.loc1.id,
            weight=1,
            do_not_schedule=False,
            notes=None,
            active_start=None,
            active_end=None,
        )
        # No weekday (applies generally), with times 13:00-17:00 for emp2
        p3 = Preference(
            employee_id=self.emp2_o1.id,
            weekday=None,
            start_time=time(13, 0),
            end_time=time(17, 0),
            role_id=self.role1.id,
            location_id=None,
            weight=3,
            do_not_schedule=False,
            notes="Afternoons",
            active_start=date(2025, 9, 1),
            active_end=None,  # open-ended
        )
        # Another org (org2) preference – should never leak into org1 queries
        p4 = Preference(
            employee_id=self.emp1_o2.id,
            weekday=5,
            start_time=time(10, 0),
            end_time=time(14, 0),
            role_id=self.role2.id,
            location_id=self.loc2.id,
            weight=2,
            do_not_schedule=False,
            notes="Org2",
            active_start=None,
            active_end=None,
        )

        self.db.add_all([p1, p2, p3, p4])
        self.db.commit()
        for p in (p1, p2, p3, p4):
            self.db.refresh(p)
        self.p1_id, self.p2_id, self.p3_id, self.p4_id = p1.id, p2.id, p3.id, p4.id

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    # -------------- GET (by id) ----------------

    def test_get_preference_found(self):
        got = service.get_preference(self.db, self.p1_id)
        self.assertIsNotNone(got)
        self.assertEqual(got.id, self.p1_id)

    def test_get_preference_not_found(self):
        got = service.get_preference(self.db, 999999)
        self.assertIsNone(got)

    def test_get_preference_for_org_ok(self):
        got = service.get_preference_for_org(self.db, self.p1_id, self.org1_id)
        self.assertIsNotNone(got)
        self.assertEqual(got.employee_id, self.emp1_o1.id)

    def test_get_preference_for_org_wrong_org_returns_none(self):
        # p1 belongs to org1 via emp1_o1; querying with org2 returns None
        got = service.get_preference_for_org(self.db, self.p1_id, self.org2_id)
        self.assertIsNone(got)

    # -------------- LIST + filters ----------------

    def test_get_preferences_scoped_to_org(self):
        rows = service.get_preferences(self.db, org_id=self.org1_id)
        ids = {r.id for r in rows}
        self.assertIn(self.p1_id, ids)
        self.assertIn(self.p2_id, ids)
        self.assertIn(self.p3_id, ids)
        self.assertNotIn(self.p4_id, ids)  # org2 excluded

    def test_get_preferences_filter_by_employee(self):
        rows = service.get_preferences(self.db, org_id=self.org1_id, employee_id=self.emp1_o1.id)
        self.assertTrue(all(r.employee_id == self.emp1_o1.id for r in rows))
        ids = {r.id for r in rows}
        self.assertIn(self.p1_id, ids)
        self.assertIn(self.p2_id, ids)
        self.assertNotIn(self.p3_id, ids)  # belongs to emp2_o1

    def test_get_preferences_filter_by_weekday(self):
        rows = service.get_preferences(self.db, org_id=self.org1_id, weekday=1)
        self.assertTrue(all(r.weekday == 1 for r in rows))
        self.assertEqual({r.id for r in rows}, {self.p1_id})

    def test_get_preferences_filter_by_role(self):
        rows = service.get_preferences(self.db, org_id=self.org1_id, role_id=self.role1.id)
        ids = {r.id for r in rows}
        self.assertIn(self.p1_id, ids)
        self.assertIn(self.p3_id, ids)
        self.assertNotIn(self.p2_id, ids)

    def test_get_preferences_filter_by_location(self):
        rows = service.get_preferences(self.db, org_id=self.org1_id, location_id=self.loc1.id)
        ids = {r.id for r in rows}
        self.assertIn(self.p1_id, ids)
        self.assertIn(self.p2_id, ids)
        self.assertNotIn(self.p3_id, ids)

    def test_get_preferences_filter_by_active_on_inside_window(self):
        # p1 active 2025-10-01..2025-10-31 ; p3 open-ended from 2025-09-01
        rows = service.get_preferences(self.db, org_id=self.org1_id, active_on=date(2025, 10, 15))
        ids = {r.id for r in rows}
        self.assertIn(self.p1_id, ids)
        self.assertIn(self.p3_id, ids)
        # p2 has no active window -> included always
        self.assertIn(self.p2_id, ids)

    def test_get_preferences_filter_by_active_on_before_window(self):
        rows = service.get_preferences(self.db, org_id=self.org1_id, active_on=date(2025, 8, 15))
        ids = {r.id for r in rows}
        # p3 (active_start 2025-09-01) should be excluded
        self.assertNotIn(self.p3_id, ids)
        # p1 (starts 2025-10-01) excluded too
        self.assertNotIn(self.p1_id, ids)
        # p2 (no window) included
        self.assertIn(self.p2_id, ids)

    def test_get_preferences_ordering(self):
        """
        ORDER BY:
          employee_id,
          Preference.weekday IS NULL,
          weekday,
          Preference.start_time IS NULL,
          start_time
        -> ensures (non-null weekday first) then by weekday, then (non-null time first) then by time.
        """
        rows = service.get_preferences(self.db, org_id=self.org1_id)
        # rows for emp1_o1 (p1 weekday=1 with time, p2 weekday=3 without time) should precede
        # the row for emp2_o1 (p3 weekday=None) due to employee_id ordering.
        emp_ids = [r.employee_id for r in rows]
        # The first two should be emp1_o1, last should be emp2_o1
        self.assertEqual(emp_ids.count(self.emp1_o1.id), 2)
        self.assertEqual(emp_ids[-1], self.emp2_o1.id)

    # -------------- CREATE ----------------

    def test_create_preference_ok(self):
        dto = PreferenceCreate(
            org_id=self.org1_id,
            employee_id=self.emp2_o1.id,
            weekday=2,
            start_time=time(8, 0),
            end_time=time(12, 0),
            role_id=self.role1.id,
            location_id=None,
            weight=7,
            do_not_schedule=False,
            notes="early",
            active_start=None,
            active_end=None,
        )
        created = service.create_preference(self.db, dto)
        self.assertIsInstance(created.id, int)
        again = self.db.get(Preference, created.id)
        self.assertIsNotNone(again)
        self.assertEqual(again.employee_id, self.emp2_o1.id)
        self.assertEqual(again.weekday, 2)
        self.assertEqual(again.start_time, time(8, 0))
        self.assertEqual(again.end_time, time(12, 0))

    def test_create_preference_cross_org_forbidden(self):
        # employee from org2 but org_id=org1 -> 403
        dto = PreferenceCreate(
            org_id=self.org1_id,
            employee_id=self.emp1_o2.id,  # org2
            weekday=4,
            start_time=None,
            end_time=None,
            role_id=None,
            location_id=None,
            weight=1,
            do_not_schedule=False,
            notes=None,
            active_start=None,
            active_end=None,
        )
        with self.assertRaises(HTTPException) as cm:
            service.create_preference(self.db, dto)
        self.assertEqual(cm.exception.status_code, 403)
        self.assertEqual(cm.exception.detail, "Cross-organization access forbidden")

    # -------------- UPDATE ----------------

    def test_update_preference_ok_partial(self):
        patch = PreferenceUpdate(
            start_time=time(10, 0),
            end_time=time(15, 0),
            notes="updated",
        )
        updated = service.update_preference(self.db, self.p2_id, patch, org_id=self.org1_id)
        self.assertEqual(updated.start_time, time(10, 0))
        self.assertEqual(updated.end_time, time(15, 0))
        self.assertEqual(updated.notes, "updated")

    def test_update_preference_404_wrong_org_or_missing(self):
        # wrong org
        patch = PreferenceUpdate(notes="x")
        with self.assertRaises(HTTPException) as cm:
            service.update_preference(self.db, self.p1_id, patch, org_id=self.org2_id)
        self.assertEqual(cm.exception.status_code, 404)
        self.assertEqual(cm.exception.detail, "Preference not found")

        # missing id
        with self.assertRaises(HTTPException) as cm2:
            service.update_preference(self.db, 999999, patch, org_id=self.org1_id)
        self.assertEqual(cm2.exception.status_code, 404)
        self.assertEqual(cm2.exception.detail, "Preference not found")

    def test_update_preference_time_pair_validation(self):
        pref = self.db.get(Preference, self.p1_id)
        pref.start_time = time(16, 0)
        pref.end_time = time(18, 0)
        self.db.commit()

        patch = PreferenceUpdate(end_time=time(12, 0))  # only one side

        with self.assertRaises(HTTPException) as cm:
            service.update_preference(self.db, self.p1_id, patch, org_id=self.org1_id)

        self.assertEqual(cm.exception.status_code, 422)
        self.assertIn("start time must be before end time", cm.exception.detail)

    def test_update_preference_active_window_validation(self):
        pref = self.db.get(Preference, self.p1_id)
        pref.active_start = date(2025, 11, 2)
        pref.active_end = None
        self.db.commit()

        # Now send ONLY active_end in the patch (schema accepts this),
        # and the service's merge-time check should raise 422.
        patch = PreferenceUpdate(active_end=date(2025, 11, 1))

        with self.assertRaises(HTTPException) as cm:
            service.update_preference(self.db, self.p1_id, patch, org_id=self.org1_id)

        self.assertEqual(cm.exception.status_code, 422)
        self.assertEqual(cm.exception.detail, "start must be on or before end")

    # -------------- DELETE ----------------

    def test_delete_preference_removes_row(self):
        service.delete_preference(self.db, self.p1_id)
        gone = self.db.get(Preference, self.p1_id)
        self.assertIsNone(gone)

    def test_delete_preference_missing_is_ok(self):
        service.delete_preference(self.db, 999999)
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
