import unittest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from core.database import Base
from organization.models import Organization
from schedule.models import Schedule, ScheduleStatus
from schedule import service
from schedule.schema import ScheduleCreate


class ScheduleServiceTests(unittest.TestCase):
    def setUp(self):
        # Fresh in-memory DB
        self.engine = create_engine("sqlite:///:memory:", future=True)
        Base.metadata.create_all(self.engine)

        Session = sessionmaker(bind=self.engine, future=True)
        self.db = Session()

        # Seed two orgs
        self.org1 = Organization(name="Org One", timezone="Atlantic/Reykjavik")
        self.org2 = Organization(name="Org Two", timezone="Atlantic/Reykjavik")
        self.db.add_all([self.org1, self.org2])
        self.db.flush()
        self.org1_id = self.org1.id
        self.org2_id = self.org2.id

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    # ---------- create_schedule ----------
    def test_create_schedule_happy_path_and_defaults(self):
        dto = ScheduleCreate(
            org_id=self.org1_id,
            created_by=123,  # can be any int in this test DB
            name="Vaktaplan vika 40",
            range_start=date(2025, 10, 1),
            range_end=date(2025, 10, 7),
            version=None,  # let service assign next version
        )
        row = service.create_schedule(self.db, dto)

        self.assertIsInstance(row.id, int)
        self.assertEqual(row.org_id, self.org1_id)
        self.assertEqual(row.name, "Vaktaplan vika 40")
        self.assertEqual(row.range_start, date(2025, 10, 1))
        self.assertEqual(row.range_end, date(2025, 10, 7))
        self.assertEqual(row.version, 1)
        self.assertEqual(row.status, ScheduleStatus.draft)
        self.assertIsNone(row.published_at)
        self.assertEqual(row.created_by, 123)

    def test_create_schedule_422_when_start_after_end(self):
        dto = ScheduleCreate(
            org_id=self.org1_id,
            created_by=1,
            name="Ógilt plan",
            range_start=date(2025, 10, 8),
            range_end=date(2025, 10, 7),
            version=None,
        )
        with self.assertRaises(HTTPException) as cm:
            service.create_schedule(self.db, dto)
        self.assertEqual(cm.exception.status_code, 422)
        self.assertEqual(cm.exception.detail, "start must be on or before end")

    def test_create_schedule_next_version_for_same_range(self):
        # First schedule -> version 1
        s1 = service.create_schedule(
            self.db,
            ScheduleCreate(
                org_id=self.org1_id,
                created_by=1,
                name="Vika 40 – útgáfa 1",
                range_start=date(2025, 10, 1),
                range_end=date(2025, 10, 7),
                version=None,
            ),
        )
        # Second schedule with same range and version=None -> version 2
        s2 = service.create_schedule(
            self.db,
            ScheduleCreate(
                org_id=self.org1_id,
                created_by=1,
                name="Vika 40 – útgáfa 2",
                range_start=date(2025, 10, 1),
                range_end=date(2025, 10, 7),
                version=None,
            ),
        )
        self.assertEqual(s1.version, 1)
        self.assertEqual(s2.version, 2)

    def test_create_schedule_duplicate_explicit_version_raises_integrity(self):
        # Create explicit version=1
        service.create_schedule(
            self.db,
            ScheduleCreate(
                org_id=self.org1_id,
                created_by=1,
                name="Vika 40 – útgáfa 1",
                range_start=date(2025, 10, 1),
                range_end=date(2025, 10, 7),
                version=1,
            ),
        )
        # Same org + range + version should violate UniqueConstraint
        with self.assertRaises(IntegrityError):
            service.create_schedule(
                self.db,
                ScheduleCreate(
                    org_id=self.org1_id,
                    created_by=1,
                    name="Vika 40 – duplicate",
                    range_start=date(2025, 10, 1),
                    range_end=date(2025, 10, 7),
                    version=1,
                ),
            )

    # ---------- get_schedules (filters + ordering) ----------
    def test_get_schedules_filters_active_on_and_org(self):
        # org1 schedules
        service.create_schedule(
            self.db,
            ScheduleCreate(
                org_id=self.org1_id,
                created_by=1,
                name="Vika 40",
                range_start=date(2025, 10, 1),
                range_end=date(2025, 10, 7),
                version=None,
            ),
        )
        service.create_schedule(
            self.db,
            ScheduleCreate(
                org_id=self.org1_id,
                created_by=1,
                name="Vika 41",
                range_start=date(2025, 10, 8),
                range_end=date(2025, 10, 14),
                version=None,
            ),
        )
        # org2 schedule (should not appear when filtering org1)
        service.create_schedule(
            self.db,
            ScheduleCreate(
                org_id=self.org2_id,
                created_by=1,
                name="Org2 vika 40",
                range_start=date(2025, 10, 1),
                range_end=date(2025, 10, 7),
                version=None,
            ),
        )

        rows = service.get_schedules(
            self.db, org_id=self.org1_id, active_on=date(2025, 10, 10)
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].range_start, date(2025, 10, 8))

    def test_get_schedules_filters_start_from_end_to(self):
        # 3 schedules in org1
        s1 = service.create_schedule(
            self.db,
            ScheduleCreate(
                org_id=self.org1_id,
                created_by=1,
                name="September",
                range_start=date(2025, 9, 1),
                range_end=date(2025, 9, 30),
                version=None,
            ),
        )
        s2 = service.create_schedule(
            self.db,
            ScheduleCreate(
                org_id=self.org1_id,
                created_by=1,
                name="Október",
                range_start=date(2025, 10, 1),
                range_end=date(2025, 10, 31),
                version=None,
            ),
        )
        s3 = service.create_schedule(
            self.db,
            ScheduleCreate(
                org_id=self.org1_id,
                created_by=1,
                name="Nóvember",
                range_start=date(2025, 11, 1),
                range_end=date(2025, 11, 30),
                version=None,
            ),
        )

        rows = service.get_schedules(
            self.db,
            org_id=self.org1_id,
            start_from=date(2025, 10, 1),
            end_to=date(2025, 11, 1),
        )
        got_ids = [r.id for r in rows]
        self.assertIn(s2.id, got_ids)
        self.assertNotIn(s1.id, got_ids)
        self.assertNotIn(s3.id, got_ids)

    def test_get_schedules_ordering_by_start_desc_then_version_desc(self):
        # Two versions for same range, plus another later range
        a1_v1 = service.create_schedule(
            self.db,
            ScheduleCreate(
                org_id=self.org1_id,
                created_by=1,
                name="Vika 40 – v1",
                range_start=date(2025, 10, 1),
                range_end=date(2025, 10, 7),
                version=1,
            ),
        )
        a1_v2 = service.create_schedule(
            self.db,
            ScheduleCreate(
                org_id=self.org1_id,
                created_by=1,
                name="Vika 40 – v2",
                range_start=date(2025, 10, 1),
                range_end=date(2025, 10, 7),
                version=2,
            ),
        )
        b_v1 = service.create_schedule(
            self.db,
            ScheduleCreate(
                org_id=self.org1_id,
                created_by=1,
                name="Vika 44",
                range_start=date(2025, 11, 1),
                range_end=date(2025, 11, 7),
                version=1,
            ),
        )

        rows = service.get_schedules(self.db, org_id=self.org1_id)
        # Expect later start date first, then higher version for same start
        self.assertEqual([r.id for r in rows], [b_v1.id, a1_v2.id, a1_v1.id])

    # ---------- get_schedule_for_org ----------
    def test_get_schedule_for_org_scopes_by_org(self):
        s1 = service.create_schedule(
            self.db,
            ScheduleCreate(
                org_id=self.org1_id,
                created_by=1,
                name="Org1 plan",
                range_start=date(2025, 10, 1),
                range_end=date(2025, 10, 7),
                version=None,
            ),
        )
        s2_other_org = service.create_schedule(
            self.db,
            ScheduleCreate(
                org_id=self.org2_id,
                created_by=1,
                name="Org2 plan",
                range_start=date(2025, 10, 1),
                range_end=date(2025, 10, 7),
                version=None,
            ),
        )

        got = service.get_schedule_for_org(self.db, s1.id, self.org1_id)
        self.assertIsNotNone(got)
        self.assertEqual(got.id, s1.id)

        got_none = service.get_schedule_for_org(
            self.db, s2_other_org.id, self.org1_id
        )
        self.assertIsNone(got_none)

    # ---------- delete_schedule ----------
    def test_delete_schedule_existing_and_missing(self):
        s1 = service.create_schedule(
            self.db,
            ScheduleCreate(
                org_id=self.org1_id,
                created_by=1,
                name="Delete me",
                range_start=date(2025, 10, 8),
                range_end=date(2025, 10, 14),
                version=None,
            ),
        )
        # delete existing
        service.delete_schedule(self.db, s1.id)
        still = self.db.get(Schedule, s1.id)
        self.assertIsNone(still)

        # delete non-existing should be no-op
        service.delete_schedule(self.db, 999999)


if __name__ == "__main__":
    unittest.main()
