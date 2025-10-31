from __future__ import annotations
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.database import get_db
from auth.services.auth_service import get_current_active_user
from authz.deps import require_manager

from .schema import (
    WeeklyTemplateSchema,
    WeeklyTemplateUpsertPayload,
    WeeklyTemplateRowUpdate,
    WeeklyTemplateGeneratePayload,
)
from . import service
from schedule.service import get_schedule_for_org

weeklytemplate_router = APIRouter(prefix="/schedules", tags=["Weekly Template"])

def _ensure_schedule_in_org(db: Session, schedule_id: int, org_id: int) -> None:
    if not get_schedule_for_org(db, schedule_id, org_id):
        # Hide existence across orgs
        raise HTTPException(status_code=404, detail="Schedule not found")


@weeklytemplate_router.get("/{schedule_id}/weekly-template", response_model=list[WeeklyTemplateSchema])
def list_weekly_template(
    schedule_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    _mgr = Depends(require_manager),
    ):
    _ensure_schedule_in_org(db, schedule_id, user.org_id)
    return service.get_weekly_template_rows(db, schedule_id=schedule_id, org_id=user.org_id)


@weeklytemplate_router.put("/{schedule_id}/weekly-template", response_model=list[WeeklyTemplateSchema])
def save_weekly_template(
    schedule_id: int,
    payload: WeeklyTemplateUpsertPayload,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    _mgr = Depends(require_manager),
    ):
    _ensure_schedule_in_org(db, schedule_id, user.org_id)
    try:
        return service.upsert_weekly_template(db, schedule_id=schedule_id, payload=payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Weekly template contains conflicting slots")


@weeklytemplate_router.patch("/{schedule_id}/weekly-template/{row_id}", response_model=WeeklyTemplateSchema)
def patch_weekly_template_row(
    schedule_id: int,
    row_id: int,
    payload: WeeklyTemplateRowUpdate,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    _mgr = Depends(require_manager),
    ):
    _ensure_schedule_in_org(db, schedule_id, user.org_id)
    try:
        row = service.update_weekly_template_row(db, schedule_id=schedule_id, row_id=row_id, patch=payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Another template row already occupies this slot")
    if not row:
        raise HTTPException(status_code=404, detail="Template row not found")
    return row


@weeklytemplate_router.delete("/{schedule_id}/weekly-template/{row_id}")
def delete_weekly_template_row_endpoint(
    schedule_id: int,
    row_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    _mgr = Depends(require_manager),
    ) -> Dict[str, Any]:
    _ensure_schedule_in_org(db, schedule_id, user.org_id)
    ok = service.delete_weekly_template_row(db, schedule_id=schedule_id, row_id=row_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Template row not found")
    return {"message": "weekly template row deleted"}


@weeklytemplate_router.post("/{schedule_id}/weekly-template/generate")
def generate_from_template_endpoint(
    schedule_id: int,
    payload: WeeklyTemplateGeneratePayload,
    db: Session = Depends(get_db),
    user = Depends(get_current_active_user),
    _mgr = Depends(require_manager),
    ) -> Dict[str, int]:
    _ensure_schedule_in_org(db, schedule_id, user.org_id)
    return service.generate_from_weekly_template(db, schedule_id=schedule_id, body=payload)
