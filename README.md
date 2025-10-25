# VaktaPlan
## Built with FastAPI + SQLAlchemy 2 + Alembic + Postgresql

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

# Get bearer token and login
export BASE_URL="http://127.0.0.1:8000/api"
export EMAIL="johanna.inga@outlook.com"
export PASS="admin"

export TOKEN=$(
  curl -sS -X POST "$BASE_URL/auth/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=$EMAIL&password=$PASS" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])'
)

## helper for curl
auth() { echo "Authorization: Bearer $TOKEN"; }
json='Content-Type: application/json'

# Routes

## User
### List all users
curl -sS "$BASE_URL/users"

### Get current users
curl -sS "$BASE_URL/users/me" -H "$(auth)"

### Get user by id
curl -sS "$BASE_URL/users/{user_id}"

### Delete user by id
curl -i -X DELETE "$BASE_URL/users/{user_id}"

### Create a user
curl -sS -X POST "$BASE_URL/users" -H "$json" \
  -d '{"username":"alice","email":"isak@example.com","password":"admin"}'

### Signup manager
curl -sS -X POST "$BASE_URL/users/signup-manager" -H "$json" \
  -d '{"org_name":"MyOrg","username":"manager","email":"manager@example.com","password":"admin"}'

## Shift

### List shifts supports filters

Query params: location_id, status (draft|published), start, end, notes

start/end are ISO8601 datetimes (TZ-aware)

curl -sS "$BASE_URL/shifts" -H "$(auth)"
curl -sS "$BASE_URL/shifts?status=published" -H "$(auth)"

###  Get a shift by id
curl -sS "$BASE_URL/shifts/{shift_id}" -H "$(auth)"

###  Create a new shift
curl -sS -X POST "$BASE_URL/shifts" -H "$json" -H "$(auth)" \
  -d '{
    "location_id": 1,
    "role_id": 1,
    "start_at": "2025-10-18T09:00:00Z",
    "end_at":   "2025-10-18T17:00:00Z",
    "status": "draft",
    "notes": "Front desk"
  }'


### Delete shift with id
curl -i -X DELETE "$BASE_URL/shifts/{shift_id}" -H "$(auth)"


###  Update Shift example
curl -sS -X PATCH "$BASE_URL/shifts/1" -H "$json" -H "$(auth)" \
  -d '{"end_at":"2025-10-18T18:00:00Z"}'

## Locations

### List all locations
curl -sS "$BASE_URL/locations" -H "$(auth)"

### Get location by id
curl -sS "$BASE_URL/locations/{location_id}" -H "$(auth)"

### Create a new location
curl -sS -X POST "$BASE_URL/locations" -H "$json" -H "$(auth)" \
  -d '{"name":"Smáralind"}'

###  Delete location with id
curl -i -X DELETE "$BASE_URL/locations/{location_id}" -H "$(auth)"


###  Update location name example
curl -sS -X PATCH "$BASE_URL/locations/1" \
  -H "$(auth)" \
  -H "$json" \
  -d '{"name":"Kringlan!"}'

## Employees

### List all employees
curl -sS "$BASE_URL/employees" -H "$(auth)"

### Get employee by id
curl -sS "$BASE_URL/employees/{employee_id}" -H "$(auth)"

### Create a new employee
curl -sS -X POST "$BASE_URL/employees" -H "$json" -H "$(auth)" \
  -d '{"display_name":"Jonas"}'

### Delete employee with id
curl -i -X DELETE "$BASE_URL/employees/{employee_id}" -H "$(auth)"

### Update employee
curl -sS -X PATCH "$BASE_URL/employees/{employee_id}" -H "$json" -H "$(auth)" \
  -d '{"display_name":"Jonas H."}'
