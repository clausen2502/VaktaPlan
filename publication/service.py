from __future__ import annotations
from datetime import date
from typing import Optional, List

from fastapi import HTTPException
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session

from .models import Publication
from .schema import PublicationCreate


# List publications for an org with optional filters
def get_publications(
    db: Session,
    *,
    org_id: int,
    active_on: Optional[date] = None,
    start_from: Optional[date] = None,
    end_to: Optional[date] = None,
) -> List[Publication]:
    stmt = select(Publication).where(Publication.org_id == org_id)

    if active_on is not None:
        stmt = stmt.where(
            and_(
                Publication.range_start <= active_on,
                Publication.range_end >= active_on,
            )
        )
    if start_from is not None:
        stmt = stmt.where(Publication.range_start >= start_from)
    if end_to is not None:
        stmt = stmt.where(Publication.range_end <= end_to)

    stmt = stmt.order_by(Publication.range_start.desc(), Publication.version.desc())
    return list(db.scalars(stmt))


# Get single publication scoped to org
def get_publication_for_org(db: Session, publication_id: int, org_id: int) -> Publication | None:
    stmt = select(Publication).where(
        Publication.id == publication_id,
        Publication.org_id == org_id,
    )
    return db.scalars(stmt).first()


def next_version_for_range(db: Session, *, org_id: int, start: date, end: date) -> int:
    maxv = db.scalar(
        select(func.max(Publication.version)).where(
            Publication.org_id == org_id,
            Publication.range_start == start,
            Publication.range_end == end,
        )
    )
    return (maxv or 0) + 1


def create_publication(db: Session, dto: PublicationCreate) -> Publication:
    if dto.range_start > dto.range_end:
        raise HTTPException(status_code=422, detail="start must be on or before end")

    version = dto.version or next_version_for_range(
        db, org_id=dto.org_id, start=dto.range_start, end=dto.range_end
    )

    row = Publication(
        org_id=dto.org_id,
        range_start=dto.range_start,
        range_end=dto.range_end,
        version=version,
        user_id=dto.user_id,
        published_at=dto.default_published_at(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_publication(db: Session, publication_id: int) -> None:
    row = db.get(Publication, publication_id)
    if row:
        db.delete(row)
        db.commit()
    return
