# VaktaPlan
## FastAPI + SQLAlchemy 2 + Alembic + Postgresql

### Run server with:
fastapi dev main.py

### Run tests with:
python -m unittest discover -s tests -p "test_*.py" -v

### layout
  router.py        # FastAPI: @get/@post endpoints
  schemas.py       # Pydantic: ShiftCreateIn, ShiftRead, etc.
  service.py       # Orchestration: DB session, repos, logic calls
  logic.py         # Domain: validate_window, detect_conflicts, compute_payable
  model.py         # SQLAlchemy: class Shift(Base)