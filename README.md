# VaktaPlan
A web application created to help managers create a schedule for their employees. 
Managers import all their employees, and shift dates and timeframe. After the manager has implemented both,
he can optionally add preferences to each employee, which for example is "John wants to preferrably work mondays",
and "John does not like working on fridays". You can also set a block in preferences, which is "John can't work on Sundays."
VaktaPlan  has an option for employees in school, where if the employee sends their school schedule, the manager can upload
the schedule to VaktaPlan and the school schedule will be read and create inputs into preferences for a specific timeframe (1 semester) where the inputs are for example "In school on mondays from 09:00 - 16:00, John can't work".
After all imports are done, the manager can get a "suggestive schedule" where VaktaPlan offers a suggested schedule, with all requirements fulfilled if it is possible. Future features would be to create an app, where employees can download the app and see their schedules in the app. Furthermore, they can view their schedule and request to change shifts, notify unavailability through the app, etc.
This is made to make schedules for manager easier and faster.

## Built with FastAPI + SQLAlchemy 2 + Alembic + Postgresql

### Run server with:
fastapi dev main.py

### Run all tests with:
python3 -m unittest discover -s tests -p "test_*.py" -v

# Instructions for login, get bearer token
export BASE_URL="http://127.0.0.1:8000/api"
export EMAIL="johanna.inga@outlook.com"
export PASS="admin"

export TOKEN=$(
  curl -sS -X POST "$BASE_URL/auth/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=$EMAIL&password=$PASS" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

## helper for curl
auth() { echo "Authorization: Bearer $TOKEN"; }
json='Content-Type: application/json'

# Routes

# User
### List all users
curl -sS "$BASE_URL/users"

### Get current user
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

# Shift

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
    "schedule_id": 1,
    "location_id": 1,
    "role_id": 1,
    "start_at": "2025-10-18T09:00:00Z",
    "end_at":   "2025-10-18T17:00:00Z",
    "notes": "Front desk"
  }'

### Delete shift with id
curl -i -X DELETE "$BASE_URL/shifts/{shift_id}" -H "$(auth)"


###  Update Shift example
curl -sS -X PATCH "$BASE_URL/shifts/1" -H "$json" -H "$(auth)" \
  -d '{"end_at":"2025-10-18T18:00:00Z"}'

# Locations

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

# Preferences

#### - Weight is used to help create a suggestion schedule.
#### - Hard block (do_not_schedule=true) where weight is ignored.
#### - Optional active window that limits when the preference applies (YYYY-MM-DD).

### List preferences (org-scoped; optionally filter by employee_id)
curl -sS "$BASE_URL/preferences" -H "$(auth)"
curl -sS "$BASE_URL/preferences?employee_id=1" -H "$(auth)"

### Get preference by id
curl -sS "$BASE_URL/preferences/{preference_id}" -H "$(auth)"

### Create preference
curl -sS -X POST "$BASE_URL/preferences" -H "$json" -H "$(auth)" \
  -d '{
    "employee_id": 1,
    "weekday": 2,
    "start_time": "09:00:00",
    "end_time": "13:00:00",
    "location_id": 1,
    "weight": 4,
    "do_not_schedule": false,
    "notes": "Loves morning shifts",
    "active_start": "2025-10-01",
    "active_end": "2025-12-31"
  }'

### Create preference (hard block)
curl -sS -X POST "$BASE_URL/preferences" -H "$json" -H "$(auth)" \
  -d '{
    "employee_id": 1,
    "weekday": 3,
    "start_time": "09:00:00",
    "end_time": "11:00:00",
    "do_not_schedule": true,
    "notes": "In school on Wednesdays",
    "active_start": "2025-10-02",
    "active_end": "2025-12-20"
  }'

### Update preference (example: flip to hard block)
curl -sS -X PATCH "$BASE_URL/preferences/{preference_id}" -H "$json" -H "$(auth)" \
  -d '{"do_not_schedule": true, "weight": null}'

### Delete preference
curl -i -X DELETE "$BASE_URL/preferences/{preference_id}" -H "$(auth)"

# Job Roles

### List job roles
curl -sS "$BASE_URL/jobroles" -H "$(auth)"

### Get job role by id
curl -sS "$BASE_URL/jobroles/{jobrole_id}" -H "$(auth)"

### Create job role
curl -sS -X POST "$BASE_URL/jobroles" \
  -H "$json" -H "$(auth)" \
  -d '{"name":"Starfsmaður á kassa"}'

### Update job role
curl -sS -X PATCH "$BASE_URL/jobroles/{jobrole_id}" \
  -H "$json" -H "$(auth)" \
  -d '{"name":"Yfirmaður Kringlunnar"}'

### Delete job role
curl -i -X DELETE "$BASE_URL/jobroles/{jobrole_id}" -H "$(auth)"

# Organization

### Get your own organization details
curl -sS "$BASE_URL/organizations/me" -H "$(auth)"

### List all organizations
curl -sS "$BASE_URL/organizations" -H "$(auth)"

### Get organization by id
curl -sS "$BASE_URL/organizations/{org_id}" -H "$(auth)"

### Create organization
curl -sS -X POST "$BASE_URL/organizations" \
  -H "$json" -H "$(auth)" \
  -d '{"name":"Dominos"}'

### helper to set your org_id
export MY_ORG_ID=$(
  curl -sS "$BASE_URL/organizations/me" -H "$(auth)" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])'
)

## Update organization with your id
curl -sS -X PATCH "$BASE_URL/organizations/{org_id}" \
  -H "$json" -H "$(auth)" \
  -d '{"name":"Domino's"}'
### or
curl -sS -X PATCH "$BASE_URL/organizations/$MY_ORG_ID" \
  -H "$json" -H "$(auth)" \
  -d "{\"name\":\"Domino's\"}"

### Delete organization
curl -i -X DELETE "$BASE_URL/organizations/{org_id}" -H "$(auth)"

### Delete your own organization
curl -i -X DELETE "$BASE_URL/organizations/me" \
  -H "$(auth)"

# Unavailability

### List unavailability (optionally filter by employee)
curl -sS "$BASE_URL/unavailability" -H "$(auth)"
curl -sS "$BASE_URL/unavailability?employee_id=1" -H "$(auth)"

### Get unavailability by id
curl -sS "$BASE_URL/unavailability/{unavail_id}" -H "$(auth)"

### Create unavailability
curl -sS -X POST "$BASE_URL/unavailability" \
  -H "$json" -H "$(auth)" \
  -d '{
    "employee_id": 1,
    "start_at": "2025-10-22T09:00:00Z",
    "end_at":   "2025-10-22T11:00:00Z",
    "reason": "Tannlæknir"
  }'

### Update unavailability
curl -sS -X PATCH "$BASE_URL/unavailability/{unavail_id}" \
  -H "$json" -H "$(auth)" \
  -d '{
    "start_at": "2025-10-22T10:00:00Z",
    "end_at":   "2025-10-22T12:00:00Z",
    "reason": "Sike ekki tannlæknir"
  }'

## Delete unavailability
curl -i -X DELETE "$BASE_URL/unavailability/{unavail_id}" -H "$(auth)"

# Assignments

### List (optionally filter by shift_id or employee_id)
curl -sS "$BASE_URL/assignments" -H "$(auth)"
curl -sS "$BASE_URL/assignments?shift_id=1" -H "$(auth)"
curl -sS "$BASE_URL/assignments?employee_id=1" -H "$(auth)"

### Get by composite id
curl -sS "$BASE_URL/assignments/{shift_id}/{employee_id}" -H "$(auth)"

### Create (manager only)
curl -sS -X POST "$BASE_URL/assignments" \
  -H "$json" -H "$(auth)" \
  -d '{"shift_id": 1, "employee_id": 1, "preference_score": 4}'

### Update (manager only, only preference_score is editable)
curl -sS -X PATCH "$BASE_URL/assignments/1/1" \
  -H "$json" -H "$(auth)" \
  -d '{"preference_score": 5}'

### Delete (manager only)
curl -i -X DELETE "$BASE_URL/assignments/{shift_id}/{employee_id}" -H "$(auth)"

# Schedules

### List schedules — optional filters
curl -sS "$BASE_URL/schedules" -H "$(auth)"

### Covering a specific date
curl -sS "$BASE_URL/schedules?active_on=2025-10-03" -H "$(auth)"

### Starting on/after a date
curl -sS "$BASE_URL/schedules?start_from=2025-10-01" -H "$(auth)"

### Ending on/before a date
curl -sS "$BASE_URL/schedules?end_to=2025-10-31" -H "$(auth)"

### Combine filters
curl -sS "$BASE_URL/schedules?start_from=2025-10-01&end_to=2025-10-31" -H "$(auth)"

### Get a schedule by id
curl -sS "$BASE_URL/schedules/{schedule_id}" -H "$(auth)"

### Create a schedule
curl -sS -X POST "$BASE_URL/schedules" \
  -H "$json" -H "$(auth)" \
  -d '{
    "range_start": "2025-10-01",
    "range_end":   "2025-10-07",
    "version": 2
  }'

### Delete a schedule
curl -i -X DELETE "$BASE_URL/schedules/{schedule_id}" -H "$(auth)"
