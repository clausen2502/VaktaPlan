# tests/test_services/test_shift_service.py
import unittest
from datetime import datetime, timezone, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from core.database import Base

from organization.models import Organization
from location.models import Location
from shift.models import Shift, ShiftStatus
from shift import service
from shift.schemas import ShiftUpdateIn
import models_bootstrap
from role.models import JobRole


class Obj:
    """Simple attribute container for payload mocks."""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class ShiftServiceTests(unittest.TestCase):
    def setUp(self):
        # Fresh in-memory DB
        self.engine = create_engine("sqlite:///:memory:", future=True)
        # IMPORTANT: models must be imported before create_all so tables exist
        Base.metadata.create_all(self.engine)

        TestingSession = sessionmaker(bind=self.engine, future=True)
        self.db = TestingSession()

        # --- seed org & location (satisfy NOT NULLs) ---
        org = Organization(name="Test Org", timezone="Atlantic/Reykjavik")  # NOT NULL
        self.db.add(org)
        self.db.flush()  # populate org.id
        self.org_id = org.id

        loc = Location(org_id=org.id, name="HQ")
        self.db.add(loc)
        self.db.flush()  # populate loc.id
        self.location_id = loc.id

        # --- seed a few shifts you can query in tests ---
        base = datetime(2025, 10, 16, 9, 0, tzinfo=timezone.utc)
        s1 = Shift(
            org_id=self.org_id, location_id=self.location_id, role_id=1,
            start_at=base, end_at=base + timedelta(hours=8),
            status=ShiftStatus.draft, notes="front desk"
        )
        s2 = Shift(
            org_id=self.org_id, location_id=self.location_id, role_id=1,
            start_at=base + timedelta(days=1),
            end_at=base + timedelta(days=1, hours=8),
            status=ShiftStatus.published, notes="mid shift"
        )
        s3 = Shift(
            org_id=self.org_id, location_id=self.location_id, role_id=2,
            start_at=base + timedelta(days=2),
            end_at=base + timedelta(days=2, hours=8),
            status=ShiftStatus.published, notes="back office"
        )
        self.db.add_all([s1, s2, s3])
        self.db.commit()
        self.db.refresh(s1); self.db.refresh(s2); self.db.refresh(s3)

        # Store ids for convenience in tests
        self.ids = [s1.id, s2.id, s3.id]

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    # ---- get_shift ----
    def test_get_shift_found(self):
        got = service.get_shift(self.db, self.ids[0])
        self.assertIsNotNone(got)
        self.assertEqual(got.id, self.ids[0])

    def test_get_shift_not_found(self):
        got = service.get_shift(self.db, 999999)
        self.assertIsNone(got)

    # ---- get_shifts: filters ----
    def test_get_shifts_all(self):
        rows = service.get_shifts(self.db)
        self.assertEqual(len(rows), 3)
        self.assertTrue(rows[0].start_at <= rows[1].start_at <= rows[2].start_at)

    def test_get_shifts_location_filter(self):
        rows = service.get_shifts(self.db, location_id=self.location_id)
        self.assertTrue(all(r.location_id == self.location_id for r in rows))
        self.assertEqual(len(rows), 3)

    def test_get_shifts_status_filter(self):
        rows = service.get_shifts(self.db, status=ShiftStatus.published)
        self.assertTrue(all(r.status == ShiftStatus.published for r in rows))
        self.assertEqual(len(rows), 2)

    def test_get_shifts_notes_ilike(self):
        rows = service.get_shifts(self.db, notes="front")
        self.assertEqual(len(rows), 1)
        self.assertIn("front", rows[0].notes)

    def test_get_shifts_time_window_overlap(self):
        # Overlaps only the middle shift (2025-10-17)
        start = datetime(2025, 10, 17, 8, 30, tzinfo=timezone.utc)
        end   = datetime(2025, 10, 17, 12, 0, tzinfo=timezone.utc)
        rows = service.get_shifts(self.db, start=start, end=end)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].start_at.date().isoformat(), "2025-10-17")

    # ---- create_shift ----
    def test_create_shift_inserts_and_returns(self):
        payload = Obj(
            org_id=self.org_id,
            location_id=self.location_id,
            role_id=3,
            start_at=datetime(2025, 10, 19, 9, 0, tzinfo=timezone.utc),
            end_at=datetime(2025, 10, 19, 17, 0, tzinfo=timezone.utc),
            status=ShiftStatus.draft,
            notes="new day",
        )
        created = service.create_shift(self.db, payload)
        self.assertIsInstance(created.id, int)

        again = service.get_shift(self.db, created.id)
        self.assertIsNotNone(again)
        self.assertEqual(again.notes, "new day")

    # ---- delete_shift ----
    def test_delete_shift_existing(self):
        victim = self.ids[1]
        service.delete_shift(self.db, victim)
        self.assertIsNone(service.get_shift(self.db, victim))

    def test_delete_shift_non_existing_no_error(self):
        # should not raise
        service.delete_shift(self.db, 999999)
        # still 3 originals remain (we didn’t delete any real row)
        rows = service.get_shifts(self.db)
        self.assertEqual(len(rows), 3)
    
    def test_update_shift_end_time_only(self):
    # Take existing shift and extend by 1 hour
        shift_id = self.ids[0]
        before = service.get_shift(self.db, shift_id)
        new_end = before.end_at + timedelta(hours=1)

        patch = ShiftUpdateIn(end_at=new_end)
        after = service.update_shift(self.db, shift_id, patch)

        assert after.id == shift_id
        assert after.end_at == new_end
        # unchanged fields remain the same
        assert after.start_at == before.start_at
        assert after.location_id == before.location_id
        assert after.status == before.status

    def test_update_shift_notes_only(self):
        shift_id = self.ids[1]
        patch = ShiftUpdateIn(notes="updated notes")
        after = service.update_shift(self.db, shift_id, patch)
        assert after.notes == "updated notes"

    def test_update_shift_invalid_dates_422(self):
        shift_id = self.ids[2]
        current = service.get_shift(self.db, shift_id)

        # Make start_at later than the already-saved end_at
        bad_start = current.end_at + timedelta(hours=1)

        # Construct WITHOUT validation so we can hit the service-level guard
        patch = ShiftUpdateIn.model_construct(start_at=bad_start)

        with self.assertRaises(HTTPException) as cm:
            service.update_shift(self.db, shift_id, patch)
        self.assertEqual(cm.exception.status_code, 422)

    def test_update_shift_not_found_404(self):
        patch = ShiftUpdateIn(notes="doesn't matter")
        with self.assertRaises(HTTPException) as cm:
            service.update_shift(self.db, 999999, patch)
        assert cm.exception.status_code == 404


if __name__ == "__main__":
    unittest.main()
