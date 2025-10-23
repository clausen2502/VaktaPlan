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

# Run instructions - curl commands
BASE="http://127.0.0.1:8000"

# Set login
BASE="http://127.0.0.1:8000"
EMAIL="johanna.inga@outlook.com"
PASS="admin"

# Get bearer token and login
TOKEN=$(curl -sS -X POST "$BASE/api/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$EMAIL&password=$PASS" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

echo "TOKEN=$TOKEN"
set TOKEN= (input_token)


## Shift
### 1) Get shift with id=1
curl -sS "$BASE/api/shifts/1"

### 2) List all shifts
curl -sS "$BASE/api/shifts/"

### 3) Create a new shift
curl -sS -X POST "$BASE/api/shifts" \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": 1,
    "location_id": 1,
    "role_id": 1,
    "start_at": "2025-10-18T09:00:00Z",
    "end_at":   "2025-10-18T17:00:00Z",
    "status": "published",
    "notes": "Demo shift 2"
  }'

### 4) Delete shift with id=2
curl -i -X DELETE "$BASE/api/shifts/2"

### 5) Update Shift example
curl -X PATCH "$BASE/api/shifts/1" \
  -H "Content-Type: application/json" \
  -d '{"end_at":"2025-10-16T18:00:00Z"}'

## Locations
