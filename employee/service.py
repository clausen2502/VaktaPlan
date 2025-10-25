from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from .models import Employee
from .schema import EmployeeCreate, EmployeeUpdate

def get_employees(db: Session, *, org_id: int) -> List[Employee]:
    statement = select(Employee).where(Employee.org_id == org_id).order_by(Employee.display_name.asc())
    return list(db.scalars(statement))

def get_employee(db: Session, employee_id: int) -> Employee:
    return db.get(Employee, employee_id)

def get_employee_for_org(db: Session, employee_id: int, org_id: int) -> Optional[Employee]:
    statement = select(Employee).where(Employee.id == employee_id, Employee.org_id == org_id)
    return db.scalars(statement).first()

def create_employee(db: Session, employee: EmployeeCreate) -> Employee:
    db_employee = Employee(org_id = employee.org_id, display_name = employee.display_name)
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)
    return db_employee

def update_employee(db: Session, employee_id: int, patch: EmployeeUpdate) -> Optional[Employee]:
    db_employee = db.get(Employee, employee_id)
    if not db_employee:
        return None
    data = patch.model_dump(exclude_unset=True)
    for k,v in data.items():
        setattr(db_employee, k, v)
    db.commit()
    db.refresh(db_employee)
    return db_employee

def delete_employee(db: Session, employee_id: int) -> None:
    db_employee = db.get(Employee, employee_id)
    if db_employee:
        db.delete(db_employee)
        db.commit()
    return
