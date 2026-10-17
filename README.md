# AI-Powered Attendance Management Platform

Secure modular-monolith attendance management platform for administrators and employees.
The selected stack is React/Vite/Material UI/Recharts on the frontend and
FastAPI/SQLAlchemy/Pydantic/PostgreSQL on the backend, with a backend-only Groq AI integration
through validated, read-only attendance report tools.

## Delivery status

This repository is being built in verified stages to meet the October 17, 2026, 4:00 PM
IST deadline. The verified implementation currently includes the runnable backend
foundation, Admin Operations, Attendance Core, Reports, and Groq-powered AI Assistant modules:

- FastAPI application with OpenAPI at `/docs`.
- Environment-based settings and PostgreSQL configuration, with SQLite available only as
  a local/test fallback when PostgreSQL is not available.
- SQLAlchemy entities for users, shifts, attendance records, and audit logs.
- Argon2 password hashing, signed JWT access tokens, active-user checks, and role-based
  access control for Admin and Employee.
- Consistent validation/application errors, liveness/readiness checks, and login audit
  events that avoid storing raw passwords or login emails.
- Admin-only employee CRUD, activation/deactivation, and safe physical deletion when no
  attendance history exists.
- Admin-only shift CRUD with IANA timezone and shift-time validation, case-insensitive
  duplicate checks, assignment validation, and safe deletion checks.
- Administrative audit events for successful employee and shift changes. Audit metadata
  contains operation/field information but no raw passwords or password values.
- Employee-scoped attendance punch-in, punch-out, current-state, and history APIs with
  server-generated UTC timestamps, shift-timezone work-date resolution, duplicate/state
  validation, and attendance audit events.
- Employee-scoped and admin-scoped monthly trends, attendance summaries, and calendar-day
  absenteeism reports using persisted attendance work dates and server-side scope rules.
- Vite React frontend with Material UI, centralized token handling, protected role-based
  navigation, admin and employee dashboards, reports charts, and a truthful unavailable
  state for the unimplemented assistant endpoint.
- Integration tests for authentication, authorization, employee/shift operations,
  duplicate inputs, inactive-user access, validation errors, audit events, safe deletion
  boundaries, attendance transitions, work-date handling, and employee data scoping.

The Gemini assistant and production migration workflow are intentionally not claimed as
implemented yet. Absenteeism is explicitly calendar-day based until schedule, leave,
holiday, and employment-period data exists.

## Repository layout

```text
.
├─ backend/
│  ├─ app/
│  │  ├─ api/routes/          # HTTP routes and dependency wiring
│  │  ├─ core/                # settings, security, time, errors, logging
│  │  ├─ db/                  # SQLAlchemy engine, session, metadata initialization
│  │  ├─ models/              # User, Shift, AttendanceRecord, AuditLog
│  │  ├─ schemas/             # Pydantic API contracts
│  │  ├─ services/            # authentication, audit, admin, attendance, and report services
│  │  ├─ cli.py               # interactive admin bootstrap command
│  │  └─ main.py              # FastAPI application
│  ├─ tests/                  # pytest API integration tests
│  ├─ requirements.txt
│  └─ .env.example
├─ frontend/
│  ├─ src/                     # React pages, API client, auth, layout, and theme
│  ├─ package.json
│  └─ .env.example
├─ docs/                      # Mermaid architecture and sequence diagrams
├─ docker-compose.yml         # PostgreSQL for local development
├─ .env.example               # Compose variables only
└─ README.md
```

The frontend uses the existing backend only; it does not contain credentials or direct
database access. The assistant screen remains visibly unavailable until a backend
assistant route exists.

## Local setup

### Prerequisites

- Python 3.13 (verified in this workspace).
- Node.js 20+ and npm (Node 20.19.2/npm 10.8.2 are available in this workspace).
- PostgreSQL 15+ for the normal development configuration.
- Docker Desktop is optional; it is not installed in the current workspace.

### Option A: run with PostgreSQL

1. Create a local, uncommitted root `.env` from `.env.example` and set the PostgreSQL
   values. These values are local development credentials and must not be committed.
2. Start PostgreSQL:

   ```powershell
   docker compose up -d postgres
   ```

3. Copy `backend/.env.example` to `backend/.env` and set `DATABASE_URL` to match the
   database above. Replace `JWT_SECRET_KEY` with a random value of at least 32 characters.
4. Install backend dependencies and start the API:

   ```powershell
   Set-Location backend
   python -m pip install -r requirements.txt
   $env:PYTHONPATH = "."
   python -m app.cli create-admin --email admin@example.com --name "Platform Admin"
   python -m uvicorn app.main:app --reload
   ```

### Option B: run without PostgreSQL for a quick local smoke test

PostgreSQL remains the target database. For a machine without PostgreSQL, copy
`backend/.env.example` to `backend/.env`, set:

```dotenv
DATABASE_URL=sqlite:///./attendance.db
JWT_SECRET_KEY=replace-this-with-a-random-32-character-value
```

Then run the same install, admin-bootstrap, and Uvicorn commands above from `backend`.
SQLite is for development/testing convenience only; PostgreSQL is required for the
deployment target.

The first startup creates the current MVP tables with SQLAlchemy `create_all`. A
versioned migration workflow will be added before production deployment.

### Run the frontend

With the backend running on `http://127.0.0.1:8000`, start the frontend from a second
terminal:

```powershell
Set-Location frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. `VITE_API_BASE_URL` defaults to
`http://127.0.0.1:8000`; set it in `frontend/.env` when the backend uses another URL.

## Environment variables

| Variable | Required | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | Yes in deployment | SQLAlchemy URL, normally `postgresql+psycopg://...` |
| `JWT_SECRET_KEY` | Yes | Random signing secret, minimum 32 characters; never commit it |
| `JWT_ALGORITHM` | No | Defaults to `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Defaults to 30; bounded to 5–1440 |
| `APP_NAME` | No | FastAPI title |
| `ENVIRONMENT` | No | Runtime environment label |
| `LOG_LEVEL` | No | Python logging level |
| `CORS_ORIGINS` | No | Comma-separated browser origins allowed to call the API |
| `GROQ_API_KEY` | Yes (for AI assistant) | Backend-only API key for Groq; never sent to the browser |
| `GROQ_MODEL` | No | Configured Groq model name; defaults to `qwen/qwen3.8-27b` |

Groq credentials are backend-only environment variables and are never sent to the browser.
When unconfigured or if the external provider is unreachable, safe deterministic fallback
responses based on verified report data are returned.

## API documentation and current routes

With the backend running:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
- Liveness: `GET /healthz`
- Database readiness: `GET /readyz`
- Login: `POST /api/v1/auth/login` with `{ "email": "...", "password": "..." }`
- Current user: `GET /api/v1/auth/me` with a Bearer JWT
- Admin account listing: `GET /api/v1/admin/users` (Admin role only)
- Employee list/create/read/update: `GET|POST /api/v1/admin/employees`,
  `GET|PATCH /api/v1/admin/employees/{employee_id}` (Admin role only)
- Employee activation/deactivation: `PATCH /api/v1/admin/employees/{employee_id}/status`
  with `{ "is_active": true|false }` (Admin role only)
- Employee deletion: `DELETE /api/v1/admin/employees/{employee_id}`; blocked with
  `409 employee_has_attendance` when attendance history exists
- Shift list/create/read/update/delete: `GET|POST /api/v1/admin/shifts`,
  `GET|PATCH|DELETE /api/v1/admin/shifts/{shift_id}` (Admin role only)
- Shift deletion is blocked with `409 shift_in_use` while employees are assigned, or
  `409 shift_has_attendance` when assigned employees have attendance history.
- Employee attendance state: `GET /api/v1/attendance/current` (Employee role only).
- Punch-in/punch-out: `POST /api/v1/attendance/punch-in` and
  `POST /api/v1/attendance/punch-out` (Employee role only). The server supplies the
  timestamp; the client cannot provide a work date or punch timestamp.
- Attendance history: `GET /api/v1/attendance/history` (Employee role only), with optional
  inclusive `from_date`/`to_date` filters and bounded `limit`/`offset` pagination.
- Reports: `GET /api/v1/reports/monthly-trends`,
  `GET /api/v1/reports/attendance-summary`, and `GET /api/v1/reports/absenteeism` with a
  required `month=YYYY-MM` query parameter. Admins may optionally provide `employee_id`;
  employees are always scoped to themselves.
- Assistant: `POST /api/v1/assistant/query` with `{ "query": "..." }`. Backed by Groq SDK,
  read-only allowlisted report tools, server-side employee/admin scoping, PII masking, and
  deterministic fallbacks.

Authentication errors do not distinguish an unknown email from a wrong password. Every
protected endpoint obtains the current user from the token and checks active status and
role on the server.

## Checks

Run from `backend` after setting `PYTHONPATH` and creating a local `.env`:

```powershell
$env:PYTHONPATH = "."
python -m pytest -q
```

The current verified result is `38 passed`. The tests use a fresh SQLite schema with
foreign-key enforcement enabled and do not require a running PostgreSQL server.
PostgreSQL readiness is exercised by the `/readyz` route when the application is
configured with PostgreSQL.

## Security controls and design decisions

- Passwords are hashed with Argon2 through `pwdlib`; plaintext passwords are never
  persisted or logged.
- JWTs are signed server-side, have an expiration, and carry only a user ID, token type,
  issue time, and expiry. The browser never receives an AI provider credential.
- Authentication and authorization are server-side dependencies. Admin-only routes use
  an explicit role dependency; employees cannot access employee or shift administration
  endpoints.
- Pydantic validates email/password input and the API returns one structured error shape
  for application and validation failures.
- Login success/failure events are persisted in `audit_logs`. Login audit metadata stores
  only a role or generic failure reason; it does not store passwords or raw login emails.
- Successful employee and shift administration changes are persisted in `audit_logs`.
  Employee deletion explicitly detaches prior audit actor references to preserve those
  audit rows while safely removing the user.
- Successful attendance punch-in and punch-out changes are also audited with only the
  attendance entity and work date; no passwords or unnecessary personal data are stored.
- Shift names have both application-level normalized duplicate checks and a database
  unique expression index on `lower(name)` for case-insensitive uniqueness under
  concurrent writes. Existing databases need the future migration workflow to receive
  schema changes; the verified tests run from a fresh SQLite schema.
- User emails are normalized at the API boundary and protected by a database unique
  expression index on `lower(email)` as well as the application duplicate check.
- Employee assignment accepts only active shifts. Employee deletion is blocked when an
  attendance record exists. Shift deletion is blocked while any employee is assigned,
  including when an assigned employee has attendance history; no relationship is silently
  nulled as part of a delete request.
- Attendance records have a database uniqueness constraint per employee/work date and a
  punch ordering constraint. Punch operations will use transactions and this constraint
  rather than trusting a client-side duplicate check.
- Timestamps are stored as UTC-aware datetimes. Work dates and shift timezone boundaries
  will be resolved in the attendance service instead of inferred in the browser.
- Overnight shifts assign punches from midnight through the configured end time to the
  prior local work date. Employees without a shift use UTC for work-date resolution.
- Reports use persisted `work_date`, include zero-valued days in monthly trends, include
  inactive employees in admin historical aggregation, and return `null` rates when there
  are no employees in scope.
- AI assistant uses official Groq Python SDK with backend-only key, server-side allowlisted
  read-only tools (`get_attendance_summary`, `get_monthly_trends`, `get_absenteeism_report`),
  server-enforced employee scoping, PII masking, and deterministic fallbacks.
- The architecture is a modular monolith. There is no Redis, Kafka, vector database, or
  microservice boundary because the required MVP does not demonstrate a need for them.

## Documentation

The Mermaid diagrams in [`docs/architecture.md`](docs/architecture.md) cover the high-level
architecture, deployment, components, database ER model, and the required authentication,
punch, and AI-query sequences.

## Planned implementation stages

1. **Backend foundation (verified):** configuration, schema, auth, RBAC, audit foundation,
   health checks, OpenAPI, and integration tests.
2. **Admin operations (verified):** employee account and shift CRUD, input validation,
   activation/deactivation, safe deletion, audit events, and authorization tests.
3. **Attendance core (verified):** employee-scoped punch-in/out transactions,
   UTC/work-date handling, duplicate/state prevention, history, audit events, and tests
   for employee data scoping. Attendance summaries remain part of the reporting stage.
4. **Reports (verified):** monthly trends, absenteeism, and attendance summaries using
   parameterized report functions, with admin/employee scope rules.
5. **AI assistant (verified):** backend-only Groq SDK integration, strict intent/tool validation,
   read-only allowlisted report tools, server-enforced scoping, PII masking, deterministic fallback,
   and scoped unit/integration tests.
6. **Frontend (verified build):** Vite React application with Material UI, authenticated
   routes, admin and employee dashboards, report charts, and an interactive assistant UI
   connected to the backend query endpoint.
7. **Release hardening:** Alembic migrations, production deployment configuration,
   security review, observability, and complete end-to-end test run.

## Known limitations in this stage

- The frontend is implemented and builds successfully; no automated browser test suite is
  configured in this workspace.
- Attendance punch, current-state, history, and report endpoints are implemented.
  Calendar-day absenteeism does not represent scheduled-shift absence until schedule and
  leave data are added.
- `create_all` is suitable for a fresh local MVP database, not production schema changes.
- No deployment has been performed from this workspace.
