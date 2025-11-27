from __future__ import annotations
from datetime import datetime, timedelta, date, timezone
from typing import Literal

from fastapi import HTTPException
from sqlalchemy import select, and_, func, delete
from sqlalchemy.orm import Session

from shift.models import Shift
from assignment.models import Assignment
from employee.models import Employee
from preference.models import Preference
from unavailability.models import Unavailability
from jobrole.models import JobRole

#TODO: Optimize auto assign service by pre-loading unavailability, 
    # preferences and existing assignments instead of querying in inner loops.

# ---------- helpers ----------

def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

def _week_bounds(d: date) -> tuple[datetime, datetime]:
    # ISO week: Monday as first day
    monday = d - timedelta(days=d.weekday())
    sunday = monday + timedelta(days=6)
    start = datetime(monday.year, monday.month, monday.day, 0, 0, 0, tzinfo=timezone.utc)
    end   = datetime(sunday.year, sunday.month, sunday.day, 23, 59, 59, tzinfo=timezone.utc)
    return start, end

def _shift_hours(s: Shift) -> float:
    return (_aware(s.end_at) - _aware(s.start_at) ).total_seconds() / 3600.0

def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return (a_start < b_end) and (a_end > b_start)

# ---------- scoring / constraints ----------

def _candidate_blocked_by_unavailability(db: Session, employee_id: int, start: datetime, end: datetime) -> bool:
    stmt = select(func.count(Unavailability.id)).where(
        and_(
            Unavailability.employee_id == employee_id,
            Unavailability.start_at < end,
            Unavailability.end_at   > start,
        )
    )
    return (db.scalar(stmt) or 0) > 0

def _preference_score(db: Session, employee_id: int, shift: Shift) -> int:
    """
    MVP scoring:
    - If any pref with do_not_schedule=True overlaps → disqualify via -infinity sentinel.
    - Else return max(weight) of overlapping prefs (default 0).
    """
    start = _aware(shift.start_at)
    end = _aware(shift.end_at)

    prefs = list(db.scalars(
        select(Preference).where(
            Preference.employee_id == employee_id,
            Preference.weekday == start.weekday(),  # filter on weekday
        )
    ))
    best = 0
    for p in prefs:
        # only use preferences in the valid date range
        if getattr(p, "active_start", None) and start.date() < p.active_start:
            continue
        if getattr(p, "active_end", None) and start.date() > p.active_end:
            continue

        # build preference window on the shift's start date
        st = datetime(
            start.year, start.month, start.day,
            p.start_time.hour, p.start_time.minute, p.start_time.second,
            tzinfo=timezone.utc,
        )
        en = datetime(
            start.year, start.month, start.day,
            p.end_time.hour, p.end_time.minute, p.end_time.second,
            tzinfo=timezone.utc,
        )
        # handle overnight prefs, e.g. 22:00–06:00
        if en <= st:
            en += timedelta(days=1)

        if _overlaps(start, end, st, en):
            if getattr(p, "do_not_schedule", False):
                return -10_000  # hard block sentinel
            best = max(best, getattr(p, "weight", 0) or 0)

    return best

def _current_week_role_hours(db: Session, employee_id: int, role_id: int, week_start: datetime, week_end: datetime,) -> float:
    """
    Sum assigned shift hours for this employee on this role within week window.
    """
    stmt = (
        select(Shift.start_at, Shift.end_at)
        .join(Assignment, Assignment.shift_id == Shift.id)
        .where(
            Assignment.employee_id == employee_id,
            Shift.role_id == role_id,
            Shift.start_at < week_end,
            Shift.end_at > week_start,
        )
    )

    total = 0.0
    for s_start, s_end in db.execute(stmt):
        total += (_aware(s_end) - _aware(s_start)).total_seconds() / 3600.0
    return total


def _role_week_cap(db: Session, role_id: int) -> float:
    return db.scalar(
        select(JobRole.weekly_hours_cap).where(JobRole.id == role_id)
    )

# ---------- fetch shifts and employees ----------

def _load_shifts_and_employees(db: Session, org_id: int, start: datetime, end: datetime):
    # shifts in window
    shifts = list(db.scalars(
        select(Shift).where(
            Shift.org_id == org_id,
            Shift.start_at < end,
            Shift.end_at   > start,
        ).order_by(Shift.start_at.asc(), Shift.id.asc())
    ))

    employees = list(db.scalars(select(Employee).where(Employee.org_id == org_id)))
    return shifts, employees

# ---------- public API ----------
def auto_assign(
    db: Session,
    *,
    schedule_id: int,
    start_date: date,
    end_date: date,
    policy: Literal["fill_missing", "reassign_all"] = "fill_missing",
    dry_run: bool = False,
    ) -> dict:
    """
    Greedy MVP:
    - Traverse shifts in window.
    - For each required seat, pick best candidate by:
      1) not overlapping unavailability
      2) not exceeding JobRole.weekly_hours_cap (per ISO week)
      3) highest preference scores: if it's a tie: lowest current week-role hours, then lowest total assigned this window
    - policy="reassign_all" clears assignments in window first.
    """
    # Derive UTC bounds for the window (Iceland == UTC)
    window_start = datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0, tzinfo=timezone.utc)
    window_end = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, tzinfo=timezone.utc)

    # Get org_id via any shift from schedule
    from schedule.models import Schedule
    sched = db.get(Schedule, schedule_id)
    if not sched:
        raise HTTPException(status_code=404, detail="schedule not found")

    # Load shifts and employees
    shifts, employees = _load_shifts_and_employees(db, sched.org_id, window_start, window_end)

    # Limit to this schedule’s shifts only
    shifts = [s for s in shifts if s.schedule_id == schedule_id]

    # Clear (policy: reassign_all)
    if policy == "reassign_all" and not dry_run:
        db.execute(
            delete(Assignment).where(
                Assignment.shift_id.in_([s.id for s in shifts])
            )
        )
        db.commit()

    # Build in-memory tally for tie-breaks: total hours this window (any role)
    emp_window_hours: dict[int, float] = {e.id: 0.0 for e in employees}
    # Pre-compute from current assignments in window
    current = db.execute(
        select(Assignment.employee_id, Shift.start_at, Shift.end_at)
        .join(Shift, Shift.id == Assignment.shift_id)
        .where(
            Shift.schedule_id == schedule_id,
            Shift.start_at < window_end,
            Shift.end_at > window_start,
        )
    ).all()
    for emp_id, s_start, s_end in current:
        emp_window_hours[emp_id] = emp_window_hours.get(emp_id, 0.0) + (
            (_aware(s_end) - _aware(s_start)).total_seconds() / 3600.0
        )

    result = {"assigned": 0, "skipped_full": 0, "skipped_no_candidates": 0, "policy": policy,}

    # GREEDY
    for sh in shifts:
        seats_needed = max(0, (sh.required_staff_count or 1))
        # How many already assigned?
        already = db.scalar(
            select(func.count(Assignment.employee_id)).where(
                Assignment.shift_id == sh.id
            )
        ) or 0
        seats_available = seats_needed - already
        if seats_available <= 0:
            result["skipped_full"] += 1
            continue

        week_start, week_end = _week_bounds(_aware(sh.start_at).date())
        role_cap = _role_week_cap(db, sh.role_id)

        # Gather candidates
        shift_hours = _shift_hours(sh)
        candidates = []
        for emp in employees:
            # Check if candiate already assigned to this shift
            exists = db.scalar(
                select(func.count(Assignment.employee_id)).where(Assignment.shift_id == sh.id, Assignment.employee_id == emp.id,)
            )
            if exists:
                continue

            # Unavailability
            if _candidate_blocked_by_unavailability(
                db, emp.id, _aware(sh.start_at), _aware(sh.end_at)
            ):
                continue

            # Weekly cap by role
            role_week_hours = _current_week_role_hours(
                db, emp.id, sh.role_id, week_start, week_end
            )
            if role_cap is not None:
                if role_week_hours + shift_hours > role_cap + 1e-6:
                    continue

            # Preference score
            score = _preference_score(db, emp.id, sh)
            if score <= -10_000:
                continue  # hard block

            # Tie-break metrics
            candidates.append(
                (
                    score,
                    role_week_hours,
                    emp_window_hours.get(emp.id, 0.0),
                    emp.id,
                )
            )

        if not candidates:
            result["skipped_no_candidates"] += 1
            continue

        # Order: higher pref score first, then lower role-week hours, then lower total window hours
        candidates.sort(key=lambda t: (-t[0], t[1], t[2], t[3]))

        # Fill seats greedily
        picked = []
        for _ in range(seats_available):
            for idx, cand in enumerate(candidates):
                score, role_week_hours, total_window_hours, emp_id = cand
                # Basic overlap guard with existing assignments (rare if constraints are consistent)
                conflict = db.scalar(
                    select(func.count(Assignment.employee_id))
                    .join(Shift, Shift.id == Assignment.shift_id)
                    .where(Assignment.employee_id == emp_id, Shift.start_at < _aware(sh.end_at),Shift.end_at > _aware(sh.start_at),)
                ) or 0
                if conflict:
                    continue

                picked_emp = emp_id
                picked.append(picked_emp)
                # update tallies in memory
                emp_window_hours[picked_emp] = emp_window_hours.get(
                    picked_emp, 0.0
                ) + shift_hours
                # remove chosen from candidate list for next seat
                candidates.pop(idx)
                break

        if picked:
            if not dry_run:
                for emp_id in picked:
                    db.add(Assignment(shift_id=sh.id, employee_id=emp_id))
                db.commit()

            # In both real run and dry_run we report how many seats we filled
            result["assigned"] += len(picked)
    return result
