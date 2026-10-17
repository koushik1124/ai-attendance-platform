# AI-Powered Attendance Management Platform

[![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.0-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-6.1-646CFF?style=flat&logo=vite&logoColor=white)](https://vitejs.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-4169E1?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Groq](https://img.shields.io/badge/Groq-AI%20SDK-F55036?style=flat)](https://groq.com/)
[![License](https://img.shields.io/badge/License-Proprietary-gray?style=flat)](#license)

A secure, enterprise-grade attendance management platform built as a modular monolith. The system pairs a high-performance **FastAPI** backend with a responsive **React 19 / Material UI** single-page application and integrates a privacy-preserving **Groq AI Assistant** governed by strict server-side scoping and allowlisted, read-only analytics tools.

---

## Overview

Modern workforce management demands precise time tracking, resilient role-based security, and actionable operational insights. Many legacy attendance systems suffer from loose client-side validation, timestamp tampering vulnerabilities, rigid timezone handling across overnight shifts, and opaque reporting data.

The **AI-Powered Attendance Management Platform** addresses these challenges directly:

- **Target Audience:** Enterprise administrators, human resources managers, operations leads, and employees across single- or multi-shift organizations.
- **Core Problem Solved:** Eliminates client-tampered timestamps, prevents overlapping attendance fraud, automates overnight shift work-date mapping, and makes attendance analytics queryable through conversational natural language without exposing database internals or PII.
- **Architectural Philosophy:** Designed as an auditable **modular monolith**. It avoids distributed system overhead (no external queues, Redis, or microservice sprawl) while maintaining clean domain boundaries: domain services encapsulate business rules, SQLAlchemy models enforce relational integrity, Pydantic schemas validate all API contracts, and an isolated AI service interacts exclusively through allowlisted tools.

---

## Key Features

### 1. Role-Based Access Control (RBAC) & Authentication
- **Dual Role System:** Enforces distinct capabilities for `admin` and `employee` roles at both the API dependency layer and UI routing shell.
- **Enterprise Password Hashing:** Powered by Argon2id (`pwdlib`), ensuring modern cryptographic hardness against GPU-accelerated hash attacks.
- **Stateless Bearer JWTs:** Signed short-lived tokens carrying subject claims; inactive or deleted accounts are blocked instantly via server-side database lookups.
- **Account Enumeration Defense:** Unified error envelopes return generic responses on failed authentication, preventing email enumeration.

### 2. Administrative Operations & Governance
- **Employee Lifecycle Management:** Admin-driven employee creation, profile updates, shift assignments, and instant account deactivation/reactivation.
- **Safe Relational Deletion:** Prevents cascading deletion anomalies; employee deletion is rejected if historical attendance records exist (`409 Conflict`), and shift deletion is blocked if employees remain assigned.
- **Normalized Uniqueness:** Case-insensitive uniqueness enforcement for emails and shift names using PostgreSQL functional unique expression indexes (`lower(email)`, `lower(name)`).
- **Shift & Timezone Modeling:** Configurable shifts supporting custom start/end times, IANA timezone strings (e.g., `America/New_York`, `Asia/Kolkata`), and working day bitmasks.

### 3. Server-Authoritative Attendance Engine
- **Tamper-Proof Time Tracking:** The client cannot supply punch timestamps or work dates. The backend generates UTC timestamps at arrival time and derives work dates server-side.
- **Overnight Shift Intelligence:** Automatically maps punches occurring between midnight and shift end to the prior local work date based on the employee's assigned shift configuration.
- **Atomic State Transitions:** Manages a deterministic progression: `NOT_PUNCHED_IN` &rarr; `PUNCHED_IN` &rarr; `PUNCHED_OUT`. Open sessions from previous dates must be resolved before new punches can occur.
- **Database-Level Concurrency Guarantees:** Relational unique constraint on `(user_id, work_date)` combined with a SQL `CHECK` constraint ensuring `punch_out_at >= punch_in_at`.

### 4. Enterprise Analytics & Decision-Ready Reporting
- **Multi-Scope Reporting:** Aggregates metrics organization-wide for administrators or isolates records to the authenticated employee.
- **Flexible Calculation Basis:** Supports both `scheduled_days` (reflecting actual shift working days and hire dates) and `calendar_days` metrics.
- **Metric Breakdown:** Computes attendance rate, absenteeism rate, present days, completed sessions, incomplete punches (missing punch-out), and total accumulated working hours.
- **Zero-Suppression Prevention:** Calendar trend series retain continuous days throughout the selected month, rendering accurate empty-day states.

### 5. Privacy-First Groq AI Assistant
- **Conversational Analytics:** Allows users to query attendance rates, monthly summaries, and absenteeism trends in natural language.
- **Allowlisted Function Calling:** The LLM cannot execute arbitrary SQL or shell commands. It can only call three bounded, read-only tools: `get_attendance_summary`, `get_monthly_trends`, and `get_absenteeism_report`.
- **Server-Enforced Scope:** Employees can only receive their own metrics even if they request company-wide data; administrators can query specific employee IDs or organizational aggregates.
- **Bidirectional PII & Credential Masking:** Automatically sanitizes queries and structured data, redacting email addresses, JWTs, Bearer tokens, and provider keys before and after model processing.
- **Deterministic Offline Fallbacks:** Gracefully falls back to pre-calculated structured report data if the Groq API key is unconfigured, rate-limited, or unreachable.

### 6. Audit Trails & Operational Observability
- **Comprehensive Event Logging:** Structured audit records track authentication successes/failures, employee lifecycle modifications, shift updates, and punch events.
- **Actor Detachment:** When an administrator is removed, prior audit log references detach safely without destroying historic audit logs.
- **Secret Sanitization:** Audit metadata stores operational context without storing raw passwords, password hashes, or login credentials.

---

## Technology Stack

| Category | Technology | Version | Purpose in Application |
| :--- | :--- | :--- | :--- |
| **Backend API** | [FastAPI](https://fastapi.tiangolo.com/) | `0.116.1` | Asynchronous REST API framework, dependency injection, and OpenAPI generation |
| **ASGI Server** | [Uvicorn](https://www.uvicorn.org/) | `0.35.0` | Production ASGI web server running the FastAPI application |
| **ORM & Data Layer** | [SQLAlchemy](https://www.sqlalchemy.org/) | `2.0.43` | Type-annotated mapped models, relational constraints, and query execution |
| **Database Driver** | [psycopg (binary)](https://www.psycopg.org/psycopg3/) | `3.2.9` | High-performance PostgreSQL 3.x database adapter |
| **Data Contracts** | [Pydantic](https://docs.pydantic.dev/) / Settings | `2.10.1` | Request/response validation, schema contracts, and environment parsing |
| **Database (Primary)** | [PostgreSQL](https://www.postgresql.org/) | `17-alpine` | Primary production-grade relational database run via Docker Compose |
| **Database (Fallback)**| [SQLite](https://sqlite.org/) | `3.x (Built-in)` | In-memory and local file database fallback with enforced foreign keys |
| **AI / LLM Engine** | [Groq Python SDK](https://github.com/groq/groq-python) | `1.7.0` | Fast inference backend using `qwen/qwen3.8-27b` with tool calling |
| **Security & Auth** | [pwdlib (argon2)](https://github.com/frankie567/pwdlib) | `0.2.1` | Cryptographic password hashing using Argon2id |
| **JWT Tokens** | [python-jose](https://github.com/mpdavis/python-jose) | `3.5.0` | Stateless HMAC-SHA256 (HS256) JWT generation and verification |
| **Frontend Core** | [React](https://react.dev/) | `19.0.0` | Declarative user interface with Context API state management |
| **Build Tooling** | [Vite](https://vitejs.dev/) | `6.1.0` | Modern ES-module build tool, rapid hot module replacement (HMR) |
| **UI Component Library**| [Material UI (MUI)](https://mui.com/) | `6.4.8` | Enterprise-grade component design system and layout primitives |
| **Data Visualization** | [Recharts](https://recharts.org/) | `2.15.1` | Declarative SVG bar charts and responsive trend graphs |
| **Client Routing** | [React Router DOM](https://reactrouter.com/) | `7.1.5` | Client-side routing, protected routes, and auth navigation guards |
| **Testing Suite** | [pytest](https://docs.pytest.org/) & [HTTPX](https://www.python-httpx.org/) | `8.4.2` / `0.28.1` | Comprehensive API integration testing and synchronous TestClient |

---

## System Architecture

The platform is designed as an auditable **modular monolith** that enforces strict separation of concerns between presentation, domain routing, business logic, persistence, and external AI integrations.

### Architecture Diagram

```mermaid
flowchart TD
    subgraph Clients["Presentation Layer (SPA)"]
        AdminUser["Administrator Browser"]
        EmpUser["Employee Browser"]
        ReactApp["React 19 + MUI SPA\n(AuthContext · AppShell · Recharts)"]
    end

    subgraph Edge["API Gateway & Ingress"]
        CORSMiddleware["CORS Middleware\n(Port & Domain Validation)"]
        FastAPIApp["FastAPI Modular Monolith\n(Uniform Error & Exception Handlers)"]
    end

    subgraph SecurityLayer["Authentication & Security Guard"]
        JWTDeps["OAuth2 Bearer Token Extraction"]
        RBAC["Role-Based Access Control\n(require_roles: Admin / Employee)"]
        Argon2["Argon2id Password Hasher (pwdlib)"]
    end

    subgraph RouteLayer["API Route Handlers (/api/v1)"]
        AuthRoute["/auth (login, /me)"]
        AdminRoute["/admin (employees, shifts, users)"]
        AttendanceRoute["/attendance (punch-in, punch-out, current, history)"]
        ReportsRoute["/reports (trends, summary, absenteeism)"]
        AssistantRoute["/assistant (/query)"]
        HealthRoute["/healthz & /readyz"]
    end

    subgraph ServiceLayer["Business Logic Services"]
        AuthService["Auth Service\n(Credential Check, Token Issuer)"]
        AdminService["Admin Service\n(Employee & Shift CRUD, Safe Deletion)"]
        AttendanceService["Attendance Service\n(Server UTC Clock, Shift TZ Engine, Overnight Resolver)"]
        ReportsService["Reports Service\n(Work-Date Aggregation, Scheduled vs Calendar Basis)"]
        AssistantService["AI Assistant Service\n(PII Masker, Intent Parser, Fallback Handler)"]
        AuditService["Audit Log Service\n(Structured Event Tracking)"]
    end

    subgraph ExternalAI["External AI Provider"]
        GroqAPI["Groq Cloud API\n(qwen/qwen3.8-27b · HTTPS Backend-Only)"]
    end

    subgraph DataStorage["Persistence Layer"]
        SQLAlchemy["SQLAlchemy 2.0 ORM Engine"]
        PostgresDB[("PostgreSQL 17 Primary Database\n(users · shifts · attendance_records · audit_logs)")]
        SQLiteDB[("SQLite Local / Test Fallback\n(attendance.db · PRAGMA foreign_keys=ON)")]
    end

    AdminUser -->|HTTPS Requests| ReactApp
    EmpUser -->|HTTPS Requests| ReactApp
    ReactApp -->|JSON REST + Bearer JWT| CORSMiddleware
    CORSMiddleware --> FastAPIApp

    FastAPIApp --> SecurityLayer
    SecurityLayer --> RouteLayer

    AuthRoute --> AuthService
    AdminRoute --> AdminService
    AttendanceRoute --> AttendanceService
    ReportsRoute --> ReportsService
    AssistantRoute --> AssistantService
    HealthRoute --> SQLAlchemy

    AuthService --> AuditService
    AdminService --> AuditService
    AttendanceService --> AuditService

    AssistantService -->|1. Sanitized Prompt & Tools| GroqAPI
    GroqAPI -->|2. Function Call Intent| AssistantService
    AssistantService -->|3. Scoped Read-Only Execution| ReportsService
    AssistantService -->|4. Masked Tool Results| GroqAPI
    GroqAPI -->|5. Synthesized Natural Language| AssistantService

    AuthService --> SQLAlchemy
    AdminService --> SQLAlchemy
    AttendanceService --> SQLAlchemy
    ReportsService --> SQLAlchemy
    AuditService --> SQLAlchemy

    SQLAlchemy -->|Production / Compose| PostgresDB
    SQLAlchemy -.->|Local Smoke Test / pytest| SQLiteDB
```

### Request Lifecycle Walkthrough

1. **Client Interaction:** A user interacts with the React single-page application. All API calls pass through the centralized `frontend/src/api/client.js` HTTP module, injecting the active Bearer JWT.
2. **Gateway & Dependency Validation:** The request reaches the FastAPI application. The `CORSMiddleware` validates allowed browser origins. FastAPI dependency injection (`app.api.deps`) extracts the JWT, verifies its signature and expiry, fetches the user from the database, confirms that the user is active, and verifies role authorization via `require_roles()`.
3. **Domain Processing:** The route passes control to the relevant domain service:
   - For an attendance punch, `AttendanceService` reads the server's UTC time, resolves the employee's assigned shift timezone, calculates the corresponding local work date, checks transition validity, and executes the operation within an atomic database transaction.
   - For an AI assistant query, `AssistantService` sanitizes the prompt, presents allowlisted tool definitions to Groq, executes the selected read-only reporting function with server-enforced scoping, masks sensitive attributes, and prompts Groq to synthesize the final verified answer.
4. **Relational Persistence & Audit:** SQLAlchemy persists changes to PostgreSQL, enforcing table constraints (unique composite keys, ordering check constraints). An audit event is asynchronously logged to `audit_logs` without storing sensitive user data.
5. **Response Delivery:** The API emits structured Pydantic response models. If an exception occurs, the unified error handler intercepts it and formats a consistent error response.

---

## Application Workflows

### 1. Authentication & Session Initialization
```text
User enters credentials (Email + Password)
  │
  ▼
POST /api/v1/auth/login
  ├── Normalize email to lowercase
  ├── Query active user from database
  ├── Verify password using Argon2id (constant-time verification)
  │
  ├── [INVALID] ──> Log auth.login_failed ──> Return 401 Unauthorized (No email enumeration)
  │
  └── [VALID]   ──> Sign HS256 JWT access token (30-min expiry)
                ──> Log auth.login_succeeded (records user ID and role)
                ──> Return access_token, expires_in, and sanitized UserRead profile
```

### 2. Punch-In and Punch-Out State Machine
```text
Employee initiates Punch In / Punch Out
  │
  ▼
POST /api/v1/attendance/punch-in  OR  POST /api/v1/attendance/punch-out
  ├── Verify Bearer JWT has UserRole.EMPLOYEE and is_active == True
  ├── Capture current server timestamp in UTC (client timestamps rejected)
  ├── Inspect assigned Shift timezone (defaults to UTC if unassigned)
  ├── Resolve work date (overnight shifts: punches between 00:00 and shift end map to prior date)
  │
  ├── Query existing AttendanceRecord for (user_id, work_date)
  │
  ├── [PUNCH-IN ACTION]
  │     ├── If record exists with punch_in_at ──> Return 409 Conflict (already_punched_in)
  │     └── If no record ──> Insert record with punch_in_at=now, punch_out_at=None
  │
  ├── [PUNCH-OUT ACTION]
  │     ├── If no record OR punch_in_at is None ──> Return 409 Conflict (not_punched_in)
  │     ├── If punch_out_at already set ─────────> Return 409 Conflict (already_punched_out)
  │     └── If valid ──> Set punch_out_at=now, verify punch_out_at >= punch_in_at
  │
  ├── Commit database transaction (enforcing SQL UNIQUE & CHECK constraints)
  ├── Record attendance.punch_in / attendance.punch_out audit event
  └── Return AttendanceStateRead with work_date and updated status
```

### 3. AI Assistant Query Flow
```text
User submits natural language prompt to AssistantPage
  │
  ▼
POST /api/v1/assistant/query {"query": "..."}
  ├── Mask incoming PII, tokens, and raw email strings in query
  ├── Check backend GROQ_API_KEY configuration
  │     └── [NOT CONFIGURED] ──> Return safe configuration guidance message
  │
  ├── Dispatch system prompt, user query, and 3 allowlisted tool definitions to Groq
  │
  ├── [Groq requests Tool Execution]
  │     ├── Validate tool name in {get_attendance_summary, get_monthly_trends, get_absenteeism_report}
  │     ├── Validate arguments (month: YYYY-MM, employee_id: positive integer)
  │     ├── Enforce role scoping:
  │     │     ├── Employee: employee_id strictly forced to authenticated user ID
  │     │     └── Admin: employee_id optional (allows single employee or org aggregate)
  │     ├── Execute read-only ReportsService query
  │     ├── Mask PII and sensitive fields in report data payload
  │     └── Return tool output JSON back to Groq
  │
  ├── [Groq synthesizes final response]
  │     ├── Mask outgoing response text
  │     └── Return AssistantQueryResponse (query, answer, tools_used, report_data)
  │
  └── [Provider Unreachable / API Error]
        └── Generate deterministic fallback answer directly from verified report data
```

---

## Project Directory Structure

```text
ai-attendance-platform/
├── .env.example                     # Root environment template for Docker Compose
├── .gitignore                       # Git ignore rules for Python, Node, and environments
├── docker-compose.yml               # Local PostgreSQL 17 Alpine database service
├── docs/
│   └── architecture.md              # Additional Mermaid diagrams and architecture notes
├── backend/
│   ├── .env.example                 # Backend environment variable template
│   ├── requirements.txt             # Pinned Python backend dependencies
│   ├── app/
│   │   ├── __init__.py
│   │   ├── cli.py                   # Administrative bootstrap CLI (create-admin)
│   │   ├── main.py                  # FastAPI application entrypoint, CORS, exception handlers
│   │   ├── api/
│   │   │   ├── deps.py              # Auth token extraction, active status, and RBAC guards
│   │   │   └── routes/
│   │   │       ├── admin.py         # Employee & shift CRUD, status toggle, safe deletion
│   │   │       ├── assistant.py     # Groq-powered natural language query endpoint
│   │   │       ├── attendance.py    # Punch-in, punch-out, current state, and history APIs
│   │   │       ├── auth.py          # Login and current user profile endpoints
│   │   │       ├── health.py        # /healthz liveness and /readyz database readiness
│   │   │       └── reports.py       # Trends, summary, and absenteeism analytics endpoints
│   │   ├── core/
│   │   │   ├── config.py            # Pydantic BaseSettings runtime configuration
│   │   │   ├── exceptions.py        # Structured AppError application exception class
│   │   │   ├── logging.py           # Standardized logger configuration
│   │   │   ├── security.py          # Argon2 password hashing and JWT encoding/decoding
│   │   │   └── time.py              # UTC-aware timestamp utility helpers
│   │   ├── db/
│   │   │   ├── base.py              # SQLAlchemy DeclarativeBase
│   │   │   ├── init.py              # Schema metadata initialization (create_all)
│   │   │   └── session.py           # Database engine, sessionmaker, and SQLite pragma
│   │   ├── models/
│   │   │   ├── attendance.py        # AttendanceRecord model with SQL CHECK & UNIQUE constraints
│   │   │   ├── audit.py             # AuditLog model for security and event tracking
│   │   │   ├── shift.py             # Shift model with timezone and working-days registry
│   │   │   └── user.py              # User model with role enum and case-insensitive index
│   │   ├── schemas/
│   │   │   ├── admin.py             # Employee and shift request/response Pydantic models
│   │   │   ├── assistant.py         # Assistant query request and structured response models
│   │   │   ├── attendance.py        # Punch states and attendance history filter schemas
│   │   │   ├── auth.py              # Login credentials and token response schemas
│   │   │   └── reports.py           # Analytics query schemas, trend points, and summaries
│   │   └── services/
│   │       ├── admin.py             # Business logic for employee/shift management
│   │       ├── assistant.py         # Groq tool calling, argument validator, PII masker
│   │       ├── attendance.py        # Server-side punch engine, overnight shift resolver
│   │       ├── audit.py             # Audit event persistence and metadata sanitizer
│   │       ├── auth.py              # Credential authentication verification
│   │       └── reports.py           # Work-date aggregation and scheduled vs calendar metrics
│   └── tests/
│       ├── conftest.py              # Isolated test database session & HTTP client fixtures
│       ├── test_admin.py            # Employee/shift CRUD, duplicate checks, RBAC tests
│       ├── test_assistant.py        # Groq tool-calling, scoping, PII masking, fallback tests
│       ├── test_attendance.py       # Punch state machine, overnight shifts, ordering tests
│       ├── test_auth.py             # Authentication, invalid credentials, JWT expiry tests
│       ├── test_cors.py             # CORS origin verification and preflight headers
│       └── test_reports.py          # Trends, summaries, absenteeism, and joining-date tests
├── frontend/
│   ├── .env.example                 # Frontend environment template
│   ├── package.json                 # Node dependencies and scripts
│   ├── vite.config.js               # Vite bundler configuration with React plugin
│   ├── index.html                   # HTML document root with Roboto typography imports
│   └── src/
│       ├── App.jsx                  # Main application router and protected route guards
│       ├── main.jsx                 # React root renderer wrapped in ThemeProvider
│       ├── theme.js                 # Custom Material UI enterprise theme configuration
│       ├── utils.js                 # Date formatting and error display helpers
│       ├── api/
│       │   └── client.js            # Fetch wrapper with Bearer token injection and error handling
│       ├── auth/
│       │   └── AuthContext.jsx      # Authentication context provider with session storage
│       ├── components/
│       │   ├── AppShell.jsx         # Responsive application shell, navigation drawer, app bar
│       │   ├── Icons.jsx            # SVG icon primitives (Dashboard, Clock, Shield, etc.)
│       │   ├── LoadingState.jsx     # Centered circular loader placeholder
│       │   └── MetricCard.jsx       # Reusable KPI dashboard card component
│       └── pages/
│           ├── AssistantPage.jsx    # Conversational Groq AI assistant chat interface
│           ├── DashboardPage.jsx    # Admin management tables & employee punch dashboard
│           ├── LoginPage.jsx        # Clean split-screen authentication screen
│           └── ReportsPage.jsx      # Visual analytics dashboard with Recharts visualizations
└── README.md
```

---

## Prerequisites

Before setting up the project locally, verify that your development environment satisfies the following requirements:

- **Python:** Version `3.13` or higher (verified on Python `3.13.5`).
- **Node.js & npm:** Node.js `20.x` or higher and npm `10.x` or higher (verified on Node `v20.19.2`, npm `10.8.2`).
- **Database (Choose one):**
  - **PostgreSQL 15+** (Recommended development target, provided via Docker Compose using PostgreSQL 17 Alpine).
  - **SQLite 3** (Default local fallback for quick smoke testing without external database installations).
- **Docker Desktop:** Optional, required only if running PostgreSQL via the provided `docker-compose.yml`.
- **Groq API Key:** Optional, required only for live LLM responses from the AI Assistant. When omitted, the assistant provides safe, deterministic report summaries automatically.

---

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/koushik1124/ai-attendance-platform.git
cd ai-attendance-platform
```

### 2. Configure Local Database

#### Option A: Run PostgreSQL via Docker Compose (Recommended)

1. Create the root `.env` file from `.env.example`:
   ```bash
   cp .env.example .env
   ```
   *(On Windows PowerShell: `Copy-Item .env.example .env`)*

2. Update `POSTGRES_PASSWORD` in `.env` with a local password:
   ```dotenv
   POSTGRES_DB=attendance
   POSTGRES_USER=attendance
   POSTGRES_PASSWORD=localdevpassword
   POSTGRES_PORT=5432
   ```

3. Start the PostgreSQL service:
   ```bash
   docker compose up -d postgres
   ```

#### Option B: Zero-Config Local Smoke Test (SQLite Fallback)

If Docker or PostgreSQL is not installed, you can run the platform using SQLite without installing any external database server. Skip Docker setup and configure `DATABASE_URL` in the next step.

---

### 3. Backend Setup

1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   - **Linux / macOS:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - **Windows PowerShell:**
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure backend environment variables:
   - **Linux / macOS:**
     ```bash
     cp .env.example .env
     ```
   - **Windows PowerShell:**
     ```powershell
     Copy-Item .env.example .env
     ```

   Open `backend/.env` and configure your settings:
   - For **PostgreSQL (Option A)**:
     ```dotenv
     DATABASE_URL=postgresql+psycopg://attendance:localdevpassword@localhost:5432/attendance
     JWT_SECRET_KEY=generate_a_random_secret_key_at_least_32_characters_long
     GROQ_API_KEY=your_groq_api_key_here
     ```
   - For **SQLite (Option B)**:
     ```dotenv
     DATABASE_URL=sqlite:///./attendance.db
     JWT_SECRET_KEY=generate_a_random_secret_key_at_least_32_characters_long
     GROQ_API_KEY=your_groq_api_key_here
     ```

5. Bootstrap the initial Administrator account:
   ```bash
   python -m app.cli create-admin --email admin@example.com --name "Platform Admin"
   ```
   *(You will be prompted interactively to enter and confirm a password of at least 8 characters).*

6. Start the FastAPI development server:
   ```bash
   python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

7. Verify backend readiness:
   - Open `http://127.0.0.1:8000/healthz` (should return `{"status":"ok"}`).
   - Open `http://127.0.0.1:8000/readyz` (verifies database connectivity).
   - Interactive Swagger API documentation: `http://127.0.0.1:8000/docs`.

---

### 4. Frontend Setup

Open a **separate terminal window**:

1. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```

2. Configure frontend environment variables:
   - **Linux / macOS:**
     ```bash
     cp .env.example .env
     ```
   - **Windows PowerShell:**
     ```powershell
     Copy-Item .env.example .env
     ```

   Ensure `VITE_API_BASE_URL` points to your backend instance:
   ```dotenv
   VITE_API_BASE_URL=http://127.0.0.1:8000
   ```

3. Install frontend dependencies:
   ```bash
   npm install
   ```

4. Start the Vite development server:
   ```bash
   npm run dev
   ```

5. Open the application in your browser:
   ```text
   http://localhost:5173
   ```
   Log in using the administrator credentials created in Step 3.5.

---

## Environment Configuration

### Backend Environment Variables (`backend/.env`)

| Variable | Required | Default Value | Purpose |
| :--- | :---: | :--- | :--- |
| `APP_NAME` | No | `AI-Powered Attendance Platform` | Application title displayed in OpenAPI docs |
| `ENVIRONMENT` | No | `development` | Runtime environment label (`development`, `production`) |
| `LOG_LEVEL` | No | `INFO` | Standard library logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `DATABASE_URL` | Yes | `sqlite:///./attendance.db` | SQLAlchemy connection URL (e.g., `postgresql+psycopg://user:pass@host:5432/db`) |
| `JWT_SECRET_KEY` | **Yes** | *None* | Cryptographic signing secret for JWTs (**must be &ge; 32 characters**) |
| `JWT_ALGORITHM` | No | `HS256` | HMAC signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | Access token lifespan in minutes (bounded between 5 and 1440) |
| `CORS_ORIGINS` | No | `http://127.0.0.1:5173,http://localhost:5173...` | Comma-separated list of allowed browser origins |
| `GROQ_API_KEY` | Optional | *None* | Backend-only Groq API key for AI assistant features |
| `GROQ_MODEL` | No | `qwen/qwen3.8-27b` | Groq model identifier used for natural language processing |

> [!CAUTION]
> Never commit `.env` files or hardcode API keys or secrets in source control. The `GROQ_API_KEY` is loaded exclusively on the backend server and is never transmitted to the browser client.

### Frontend Environment Variables (`frontend/.env`)

| Variable | Required | Default Value | Purpose |
| :--- | :---: | :--- | :--- |
| `VITE_API_BASE_URL` | No | `http://127.0.0.1:8000` | Target URL of the backend FastAPI REST API |

### Docker Compose Variables (`.env` at root)

| Variable | Required | Default Value | Purpose |
| :--- | :---: | :--- | :--- |
| `POSTGRES_DB` | Yes | `attendance` | Initial database name |
| `POSTGRES_USER` | Yes | `attendance` | PostgreSQL master username |
| `POSTGRES_PASSWORD`| Yes | *None* | PostgreSQL master password |
| `POSTGRES_PORT` | No | `5432` | Exposed host port for PostgreSQL service |

---

## Database Architecture and Setup

### Schema Initialization
Database tables are initialized automatically on application startup via the FastAPI `lifespan` hook (`app.main:lifespan`), which calls `Base.metadata.create_all(bind=engine)`. For local development and fresh installations, no manual migration scripts are required.

### Database Connection Management
The database session manager (`app.db.session`) configures SQLAlchemy with connection pooling and health checking:
- `pool_pre_ping=True`: Detects stale or dropped connections and reconnects automatically.
- **SQLite Foreign Key Enforcement:** When SQLite is detected, an event listener automatically triggers `PRAGMA foreign_keys=ON` on every connection to maintain relational integrity parity with PostgreSQL.

### Entity Relational Schema

```text
 ┌──────────────────────┐             ┌──────────────────────┐
 │        SHIFTS        │             │        USERS         │
 ├──────────────────────┤             ├──────────────────────┤
 │ id (PK, int)         │ 1         * │ id (PK, int)         │
 │ name (UK, str)       ├────────────<┤ email (UK, str)      │
 │ start_time (time)    │             │ full_name (str)      │
 │ end_time (time)      │             │ password_hash (str)  │
 │ timezone (str)       │             │ role (admin/employee)│
 │ is_active (bool)     │             │ is_active (bool)     │
 │ created_at (datetime)│             │ shift_id (FK, int)   │
 └──────────────────────┘             │ created_at (datetime)│
                                      │ updated_at (datetime)│
                                      └──────────┬───────────┘
                                                 │ 1
                                                 │
                         ┌───────────────────────┴───────────────────────┐
                         │ *                                             │ *
              ┌──────────▼───────────┐                        ┌──────────▼───────────┐
              │  ATTENDANCE_RECORDS  │                        │      AUDIT_LOGS      │
              ├──────────────────────┤                        ├──────────────────────┤
              │ id (PK, int)         │                        │ id (PK, int)         │
              │ user_id (FK, int)    │                        │ actor_user_id (FK)   │
              │ work_date (date)     │                        │ action (str)         │
              │ punch_in_at (dt)     │                        │ entity_type (str)    │
              │ punch_out_at (dt)    │                        │ entity_id (str)      │
              │ created_at (datetime)│                        │ metadata_json (json) │
              │ updated_at (datetime)│                        │ ip_address (str)     │
              └──────────────────────┘                        │ created_at (datetime)│
                                                              └──────────────────────┘
```

### Relational Integrity Constraints
1. **Case-Insensitive Uniqueness:** Unique expression indexes on `lower(users.email)` and `lower(shifts.name)` guarantee duplicate protection regardless of casing.
2. **Attendance Uniqueness:** Unique composite constraint on `(attendance_records.user_id, attendance_records.work_date)` prevents duplicate records on the same work date.
3. **Punch Ordering:** Database check constraint `ck_attendance_punch_order` guarantees `punch_out_at >= punch_in_at` whenever both values are populated.
4. **Audit Log Persistence:** Foreign key on `audit_logs.actor_user_id` allows nullification upon user deletion, preserving historical audit trails.

---

## Authentication and Authorization

### Mechanism
The platform uses stateless JSON Web Tokens (JWT) signed with HMAC-SHA256 (`HS256`).

- **Token Contents:** Subject claim (`sub`: user ID string), token type (`type`: `access`), issued-at (`iat`), and expiration timestamp (`exp`).
- **Server-Side Validation:** Every authenticated request executes `get_current_user` in `app/api/deps.py`. It decodes the token, queries the user by primary key, and verifies that `is_active == True`. Revoked or deactivated accounts are rejected on their subsequent request.
- **Role Enforcement:** Route endpoints declare role requirements using the `require_roles()` dependency:
  - `require_roles(UserRole.ADMIN)`: Enforced on all administrative employee and shift management endpoints.
  - `require_roles(UserRole.EMPLOYEE)`: Enforced on punch-in, punch-out, current state, and employee history endpoints.
  - Common Endpoints: Endpoints like `/api/v1/auth/me`, `/api/v1/reports/*`, and `/api/v1/assistant/query` accept any authenticated role and apply internal data scoping.

### Demo Account Creation
To create an administrative account, use the management CLI:
```bash
python -m app.cli create-admin --email admin@example.com --name "Platform Admin"
```
Employee accounts can subsequently be created through the Admin Dashboard UI or via `POST /api/v1/admin/employees`.

---

## API Documentation

Interactive API documentation is generated automatically by FastAPI and accessible locally:
- **Swagger UI:** `http://127.0.0.1:8000/docs`
- **ReDoc:** `http://127.0.0.1:8000/redoc`
- **OpenAPI Schema:** `http://127.0.0.1:8000/openapi.json`

### Primary Endpoint Reference

| Method | Endpoint | Description | Auth Required | Permitted Roles |
| :--- | :--- | :--- | :---: | :---: |
| `GET` | `/healthz` | Application liveness check | No | Public |
| `GET` | `/readyz` | Database connectivity readiness check | No | Public |
| `POST` | `/api/v1/auth/login` | Authenticate user; returns JWT token & user profile | No | Public |
| `GET` | `/api/v1/auth/me` | Fetch authenticated user's profile | Yes | Admin, Employee |
| `GET` | `/api/v1/admin/users` | List all platform users | Yes | Admin |
| `GET` | `/api/v1/admin/employees` | List all employee accounts with assigned shifts | Yes | Admin |
| `POST` | `/api/v1/admin/employees` | Create a new employee account | Yes | Admin |
| `GET` | `/api/v1/admin/employees/{id}` | Retrieve details for a specific employee | Yes | Admin |
| `PATCH` | `/api/v1/admin/employees/{id}` | Update employee profile or shift assignment | Yes | Admin |
| `PATCH` | `/api/v1/admin/employees/{id}/status` | Activate or deactivate an employee account | Yes | Admin |
| `DELETE`| `/api/v1/admin/employees/{id}` | Delete employee (blocked if attendance exists) | Yes | Admin |
| `GET` | `/api/v1/admin/shifts` | List all organizational shifts | Yes | Admin |
| `POST` | `/api/v1/admin/shifts` | Create a new shift definition | Yes | Admin |
| `GET` | `/api/v1/admin/shifts/{id}` | Retrieve details for a specific shift | Yes | Admin |
| `PATCH` | `/api/v1/admin/shifts/{id}` | Update shift parameters (times, timezone, name) | Yes | Admin |
| `DELETE`| `/api/v1/admin/shifts/{id}` | Delete shift (blocked if employees are assigned) | Yes | Admin |
| `POST` | `/api/v1/attendance/punch-in` | Punch in for the current work date | Yes | Employee |
| `POST` | `/api/v1/attendance/punch-out`| Punch out of the current active session | Yes | Employee |
| `GET` | `/api/v1/attendance/current` | Get current attendance status and today's record | Yes | Employee |
| `GET` | `/api/v1/attendance/history` | Paginated attendance history with date filters | Yes | Employee |
| `GET` | `/api/v1/reports/monthly-trends`| Daily attendance trend points for a given month | Yes | Admin, Employee |
| `GET` | `/api/v1/reports/attendance-summary` | Aggregated attendance KPI summary | Yes | Admin, Employee |
| `GET` | `/api/v1/reports/absenteeism` | Absenteeism metrics (scheduled vs calendar) | Yes | Admin, Employee |
| `POST` | `/api/v1/assistant/query` | Query natural-language attendance assistant | Yes | Admin, Employee |

### Standardized Error Format

All application errors and validation failures adhere to a consistent JSON response structure:

```json
{
  "error": {
    "code": "invalid_credentials",
    "message": "Email or password is incorrect.",
    "details": null
  }
}
```

Validation errors (`422 Unprocessable Entity`) include field locations and violation details:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "details": [
      {
        "location": ["query", "month"],
        "message": "month must use YYYY-MM format",
        "type": "value_error"
      }
    ]
  }
}
```

---

## AI Assistant Architecture and Safety

The platform's AI Assistant is powered by the official **Groq Python SDK** and uses `qwen/qwen3.8-27b` by default. It provides natural language answers strictly grounded in verified database reporting data.

### Tool Call Allowlist
The assistant does not execute arbitrary SQL or raw database queries. It has access to exactly three read-only reporting tools:

1. `get_attendance_summary(month, employee_id)`: Fetches present days, completed sessions, incomplete records, absent days, and overall attendance percentage.
2. `get_monthly_trends(month, employee_id)`: Returns daily attendance data points for the specified month.
3. `get_absenteeism_report(month, employee_id)`: Computes absenteeism rates against expected working days.

### Multi-Tiered Safety Controls
1. **Server-Side Authorization & Scope Isolation:**
   When an employee queries the assistant, the backend overrides any model-generated `employee_id` argument to the employee's own ID. Employees cannot inspect organizational metrics or peer records. Administrators can query organizational aggregates or filter to a specific employee.
2. **Two-Way PII and Credential Masking:**
   The `mask_text()` and `mask_report_data()` utilities redact email addresses (`[REDACTED_EMAIL]`), Groq API keys (`[REDACTED_API_KEY]`), Bearer tokens, and JWT strings from both incoming user prompts and outgoing tool execution payloads.
3. **Deterministic Fallbacks:**
   If the Groq API key is unconfigured, unreachable, or returns a rate-limit error, the assistant falls back to pre-calculated structured report summaries, guaranteeing reliable answers even during third-party outages.

---

## Testing and Verification

The backend includes a comprehensive integration test suite built with **pytest** and **HTTPX**. Tests run against an isolated SQLite test database with foreign keys enforced, validating all business logic, role boundaries, concurrency constraints, and AI workflows without requiring an active PostgreSQL instance.

### Running Backend Tests

Navigate to the `backend` directory with your virtual environment activated:

```powershell
# Windows PowerShell
$env:PYTHONPATH = "."
python -m pytest -v
```

```bash
# Linux / macOS
PYTHONPATH=. python -m pytest -v
```

### Verified Test Suite Breakdown (51 Passed Tests)

- **Admin Operations (`test_admin.py` - 9 tests):**
  - Employee CRUD, profile updates, and active status toggling.
  - Safe deletion boundaries (blocking deletion when attendance history exists).
  - Shift CRUD, working day bitmasks, and conflict blocking when assigned.
  - Case-insensitive email and shift name uniqueness enforcement.
  - Consistent error envelopes and RBAC protection.
- **AI Assistant (`test_assistant.py` - 11 tests):**
  - Prompt and structured report PII and secret masking.
  - Mandatory authentication and empty query validation.
  - Employee scoping enforcement and admin aggregate access.
  - Tool allowlisting rejection for unauthorized functions.
  - Graceful deterministic fallbacks during provider outages and unconfigured states.
- **Attendance Engine (`test_attendance.py` - 12 tests):**
  - Punch-in, punch-out, current state, and paginated history.
  - Prevention of duplicate punches and out-of-order transitions.
  - Shift timezone work-date resolution and overnight shift rollover handling.
  - Working hours and seconds computation.
- **Authentication & Security (`test_auth.py` - 6 tests):**
  - Health (`/healthz`) and readiness (`/readyz`) probes.
  - Token issuance, `/me` profile retrieval, and token expiration.
  - Non-enumerating credential rejection and Bearer token enforcement.
- **CORS Verification (`test_cors.py` - 5 tests):**
  - Preflight `OPTIONS` validation across authorized development ports (`5173`, `5174`, `localhost`, `127.0.0.1`).
  - Rejection of unauthorized origins.
- **Analytics & Reports (`test_reports.py` - 8 tests):**
  - Scoped monthly trends, attendance summaries, and absenteeism.
  - Mid-month hires, joining date filtering, and unworked weekend exclusion.
  - Agreement between summary aggregates and daily trend points.

### Building Frontend Assets

Verify that the frontend builds without errors:

```bash
cd frontend
npm run build
```
*(Produces optimized static production bundles in `frontend/dist`).*

---

## Screenshots and UI Walkthrough

The platform features a modern, clean web interface built with **Material UI (MUI v6)** and responsive data visualizations powered by **Recharts**.

### Key Application Views

1. **Authentication Screen (`/login`):**
   - Clean split-screen layout with email and password inputs.
   - Standardized error alerts with zero account enumeration.
2. **Admin Operations Dashboard (`/dashboard`):**
   - Organization-wide metric cards (total employees, active shifts, today's punches).
   - Employee directory with search, shift assignment, status toggle, and safe deletion.
   - Shift management panel supporting custom start/end times and IANA timezones.
3. **Employee Punch Dashboard (`/dashboard`):**
   - Real-time work date and assigned shift display.
   - Dynamic punch action card with clear state badges (`Not Punched In`, `Punched In`, `Punched Out`).
   - Personal attendance history table displaying punch timestamps, work dates, and session hours.
4. **Analytics & Reports (`/reports`):**
   - Monthly trend bar charts visualizing daily present vs. absent counts.
   - Metric summary cards (attendance rate, present employee-days, incomplete records, absenteeism rate).
   - Filter controls allowing administrators to switch between organizational aggregates and individual employee views.
5. **Conversational AI Assistant (`/assistant`):**
   - Chat interface with quick prompt chips for attendance summaries and trends.
   - Tool execution indicator chips showing verified data sources.
   - PII protection badge highlighting privacy preservation.

> [!NOTE]
> Static screenshots can be captured directly from your local browser instance once both backend and frontend servers are launched.

---

## Troubleshooting

### 1. Backend Startup Errors

- **Error:** `ValidationError: 1 validation error for Settings jwt_secret_key`
  - **Cause:** `JWT_SECRET_KEY` in `backend/.env` is either missing or shorter than 32 characters.
  - **Resolution:** Generate a random 32+ character string (e.g. `openssl rand -hex 32`) and assign it to `JWT_SECRET_KEY`.

- **Error:** `psycopg.OperationalError: connection failed`
  - **Cause:** PostgreSQL is not running or the database credentials in `DATABASE_URL` are incorrect.
  - **Resolution:** If using Docker Compose, verify container status using `docker compose ps`. If testing locally without Docker, set `DATABASE_URL=sqlite:///./attendance.db` in `backend/.env`.

### 2. Deletion Conflicts (`409 Conflict`)

- **Error:** `409 Conflict - employee_has_attendance`
  - **Cause:** Attempting to delete an employee who has historical attendance records.
  - **Resolution:** This is an intentional data integrity guard. Deactivate the employee instead using `PATCH /api/v1/admin/employees/{id}/status` with `{"is_active": false}`.

- **Error:** `409 Conflict - shift_in_use`
  - **Cause:** Attempting to delete a shift while employees are actively assigned to it.
  - **Resolution:** Reassign all assigned employees to another active shift before deleting the target shift.

### 3. Frontend & CORS Issues

- **Error:** `Failed to fetch` or CORS error in browser console
  - **Cause:** The frontend is running on a port or host not listed in the backend's `CORS_ORIGINS`.
  - **Resolution:** Verify that `CORS_ORIGINS` in `backend/.env` contains your frontend address (defaults include `http://127.0.0.1:5173`, `http://localhost:5173`, `http://127.0.0.1:5174`, `http://localhost:5174`). Restart Uvicorn after updating.

### 4. AI Assistant Fallback Behavior

- **Behavior:** The assistant returns a message stating that it is unconfigured or returns a deterministic summary instead of a custom conversational response.
  - **Cause:** `GROQ_API_KEY` is not defined in `backend/.env`, or the Groq service is temporarily unreachable.
  - **Resolution:** Add a valid Groq API key to `backend/.env` as `GROQ_API_KEY=gsk_...` and restart the backend. The platform is designed to continue operating seamlessly with deterministic fallbacks when Groq is unavailable.

---

## Security Considerations

- **Argon2id Password Hashing:** User passwords are never persisted in plaintext. Argon2id provides memory-hard hashing resistant to GPU cracking.
- **Short-Lived Stateless Tokens:** Access tokens expire automatically after 30 minutes, minimizing window of exposure if a token is intercepted.
- **Server-Authoritative Clock:** Work dates and punch timestamps are generated by the server UTC clock. Clients cannot forge historical or future attendance records.
- **Tamper-Resistant Scoping:** Scoping rules for employees are hardcoded at the backend service layer and cannot be bypassed via URL manipulation or client payload tampering.
- **PII & Credential Scrubbing:** Prompts, logs, and audit entries redact sensitive user emails, API keys, and JWT tokens.
- **Auditing Integrity:** Administrative modifications, logins, and attendance transactions produce immutable audit logs with detached foreign keys to prevent orphan log loss.

---

## Future Roadmap

The following enhancements are planned for future versions of the platform:

1. **Alembic Database Migrations:** Transition schema management from `Base.metadata.create_all` to versioned, reversible Alembic migration scripts for zero-downtime production deployments.
2. **Advanced Leave & Holiday Modeling:** Extend the reporting engine to account for statutory holidays, approved annual leave, and sick leaves in absenteeism calculations.
3. **Automated Missed Punch Detection:** Background worker task to identify and flag incomplete punch records at shift conclusion.
4. **Report Export Capabilities:** One-click CSV, Excel, and PDF export functionality for monthly attendance and absenteeism reports.
5. **Departmental Hierarchy:** Multi-tier permission roles allowing Department Managers to oversee assigned teams without full platform administrator access.

---

