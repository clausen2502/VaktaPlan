# tests/test_services/test_publication_service.py
import unittest
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.database import Base
from sqlalchemy.orm import Session

from organization.models import Organization
from publication.models import Publication
from publication import service
from publication.schema import PublicationCreate


class PublicationServiceTests(unittest.TestCase):
    def setUp(self):
        # Fresh in-memory DB
        self.engine = create_engine("sqlite:///:memory:", future=True)
        Base.metadata.create_all(self.engine)

        TestingSession = sessionmaker(bind=self.engine, future=True)
        self.db: Session = TestingSession()

        # Seed organizations
        o1 = Organization(name="Org One", timezone="Atlantic/Reykjavik")
        o2 = Organization(name="Org Two", timezone="Atlantic/Reykjavik")
        self.db.add_all([o1, o2])
        self.db.flush()
        self.org1_id = o1.id
        self.org2_id = o2.id
        self.db.commit()

        # Common window
        self.start = date(2025, 10, 1)
        self.end = date(2025, 10, 7)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    # ---------- get_publications ----------

    def test_get_publications_initial_empty(self):
        rows = service.get_publications(self.db, org_id=self.org1_id)
        self.assertEqual(rows, [])

    def test_get_publications_after_inserts(self):
        # Insert 2 versions for same window + 1 for another org
        dto1 = PublicationCreate(
            org_id=self.org1_id,
            range_start=self.start,
            range_end=self.end,
            version=1,
            user_id=123,
        )
        service.create_publication(self.db, dto1)

        dto2 = PublicationCreate(
            org_id=self.org1_id,
            range_start=self.start,
            range_end=self.end,
            version=2,
            user_id=124,
        )
        service.create_publication(self.db, dto2)

        dto_other = PublicationCreate(
            org_id=self.org2_id,
            range_start=self.start,
            range_end=self.end,
            version=1,
            user_id=200,
        )
        service.create_publication(self.db, dto_other)

        rows = service.get_publications(self.db, org_id=self.org1_id)
        self.assertEqual(len(rows), 2)
        # Ordered by range_start desc, then version desc
        self.assertEqual(rows[0].version, 2)
        self.assertEqual(rows[1].version, 1)

    def test_get_publications_filters(self):
        # Org1: two windows
        service.create_publication(self.db, PublicationCreate(
            org_id=self.org1_id, range_start=date(2025, 9, 1), range_end=date(2025, 9, 7),
            version=1, user_id=1
        ))
        service.create_publication(self.db, PublicationCreate(
            org_id=self.org1_id, range_start=date(2025, 10, 1), range_end=date(2025, 10, 7),
            version=1, user_id=1
        ))
        # Org2: one window (should never appear when filtering org1)
        service.create_publication(self.db, PublicationCreate(
            org_id=self.org2_id, range_start=date(2025, 10, 1), range_end=date(2025, 10, 7),
            version=1, user_id=9
        ))

        # active_on within Oct window → only that one for org1
        rows = service.get_publications(self.db, org_id=self.org1_id, active_on=date(2025, 10, 3))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].range_start, date(2025, 10, 1))
        self.assertEqual(rows[0].range_end, date(2025, 10, 7))

        # start_from filter (>= Oct 1) → only Oct window for org1
        rows = service.get_publications(self.db, org_id=self.org1_id, start_from=date(2025, 10, 1))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].range_start, date(2025, 10, 1))
        self.assertEqual(rows[0].range_end, date(2025, 10, 7))

        # end_to filter (<= Sep 30) → Sep window qualifies (ends Sep 7 ≤ Sep 30)
        rows = service.get_publications(self.db, org_id=self.org1_id, end_to=date(2025, 9, 30))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].range_start, date(2025, 9, 1))
        self.assertEqual(rows[0].range_end, date(2025, 9, 7))

        # Combined filter example: windows fully in September (start_from & end_to bracket)
        rows = service.get_publications(
            self.db,
            org_id=self.org1_id,
            start_from=date(2025, 9, 1),
            end_to=date(2025, 9, 30),
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].range_start, date(2025, 9, 1))
        self.assertEqual(rows[0].range_end, date(2025, 9, 7))


    # ---------- get_publication_for_org ----------

    def test_get_publication_for_org_ok_and_none(self):
        created = service.create_publication(self.db, PublicationCreate(
            org_id=self.org1_id, range_start=self.start, range_end=self.end,
            version=1, user_id=321
        ))

        got = service.get_publication_for_org(self.db, created.id, org_id=self.org1_id)
        self.assertIsNotNone(got)
        self.assertEqual(got.id, created.id)

        none = service.get_publication_for_org(self.db, created.id, org_id=self.org2_id)
        self.assertIsNone(none)

    # ---------- next_version_for_range ----------

    def test_next_version_for_range_empty_is_1(self):
        v = service.next_version_for_range(self.db, org_id=self.org1_id, start=self.start, end=self.end)
        self.assertEqual(v, 1)

    def test_create_publication_computes_next_version(self):
        # First insert w/out version → computes to 1
        dto1 = PublicationCreate(
            org_id=self.org1_id, range_start=self.start, range_end=self.end,
            user_id=111
        )
        service.create_publication(self.db, dto1)

        # Second insert w/out version → computes to 2
        dto2 = PublicationCreate(
            org_id=self.org1_id, range_start=self.start, range_end=self.end,
            user_id=222
        )
        row = service.create_publication(self.db, dto2)
        self.assertEqual(row.version, 2)

    def test_create_publication_uses_provided_version(self):
        dto = PublicationCreate(
            org_id=self.org1_id, range_start=self.start, range_end=self.end,
            version=5, user_id=111
        )
        row = service.create_publication(self.db, dto)
        self.assertEqual(row.version, 5)

    def test_create_publication_invalid_range_raises_422(self):
        with self.assertRaises(Exception) as ctx:
            service.create_publication(self.db, PublicationCreate(
                org_id=self.org1_id,
                range_start=date(2025, 10, 8),
                range_end=date(2025, 10, 7),
                user_id=1,
            ))
        self.assertIn("start must be on or before end", str(ctx.exception))

    # ---------- delete_publication ----------

    def test_delete_publication_deletes(self):
        created = service.create_publication(self.db, PublicationCreate(
            org_id=self.org1_id, range_start=self.start, range_end=self.end,
            version=1, user_id=777
        ))
        pid = created.id

        service.delete_publication(self.db, pid)
        self.assertIsNone(self.db.get(Publication, pid))


if __name__ == "__main__":
    unittest.main()
