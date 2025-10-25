from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.database import get_db
from auth.services.auth_service import get_current_active_user
from .schema import EmployeeSchema, EmployeeCreatePayload, EmployeeCreate, EmployeeUpdate
from . import service

employee_router = APIRouter(prefix="/employees", tags=["Employees"])

# List all employees
@employee_router.get("", response_model=list[EmployeeSchema])
def list_employees(db: Session = Depends(get_db), user=Depends(get_current_active_user)):
    return service.get_employees(db, org_id=user.org_id)

# Get employee by id
@employee_router.get("/{employee_id}", response_model=EmployeeSchema)
def employee_detail(employee_id: int, db: Session = Depends(get_db), user=Depends(get_current_active_user)):
    obj = service.get_employee_for_org(db, employee_id, user.org_id)
    if not obj:
        raise HTTPException(status_code=404, detail="employee not found")
    return obj

# Create employee
@employee_router.post("", response_model=EmployeeSchema, status_code=status.HTTP_201_CREATED)
def employee_post(payload: EmployeeCreatePayload, db: Session = Depends(get_db), user=Depends(get_current_active_user)):
    internal = EmployeeCreate(org_id=user.org_id, display_name=payload.display_name)
    try:
        return service.create_employee(db, internal)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail="employee name already exists in this organization")

# Update employee
@employee_router.patch("/{employee_id}", response_model=EmployeeSchema)
def employee_patch(employee_id: int, payload: EmployeeUpdate, db: Session = Depends(get_db), user=Depends(get_current_active_user)):
    obj = service.get_employee_for_org(db, employee_id, user.org_id)
    if not obj:
        raise HTTPException(status_code=404, detail="employee not found")
    return service.update_employee(db, employee_id, payload)

# Delete employee
@employee_router.delete("/{employee_id}")
def employee_delete(employee_id: int, db: Session = Depends(get_db), user=Depends(get_current_active_user)):
    obj = service.get_employee_for_org(db, employee_id, user.org_id)
    if not obj:
        raise HTTPException(status_code=404, detail="employee not found")
    service.delete_employee(db, employee_id)
    return {"message": "employee deleted"}