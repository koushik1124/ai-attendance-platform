# Platform architecture diagrams

These diagrams describe the modular-monolith MVP boundary. Solid paths are part of the
current backend foundation or intended server flow; modules marked **planned** are not
claimed to be implemented until their stage is verified.

## High-level architecture

```mermaid
flowchart LR
    Browser[Employee/Admin Browser\nReact + Vite + MUI + Recharts]
    API[FastAPI Modular Monolith\nJWT/RBAC + validation]
    DB[(PostgreSQL\nprimary database)]
    Audit[Audit log tables]
    Reports[Validated report functions\nread-only + scoped]
    AI[Gemini API\nbackend-only]
    Mask[PII masking + response policy]

    Browser -->|HTTPS JSON + Bearer JWT| API
    API -->|SQLAlchemy transactions| DB
    API --> Audit
    API --> Reports
    Reports --> DB
    API -->|validated prompt only| AI
    AI --> Mask
    Mask --> API
    API --> Browser
```

The browser never talks directly to PostgreSQL or Gemini. The API authenticates every
protected request, applies role and employee scope, and only then reads data or invokes a
validated read-only report tool.

## Deployment diagram

```mermaid
flowchart TB
    subgraph ClientZone[User device]
        Browser[Modern browser\nReact SPA]
    end

    subgraph AppZone[Application environment]
        Edge[HTTPS reverse proxy / ingress\nTLS + security headers]
        App[FastAPI application\nmodular monolith]
        Worker[Optional scheduled job runner\nplanned; no queue required for MVP]
    end

    subgraph DataZone[Private data network]
        PostgreSQL[(Managed PostgreSQL)]
        Secrets[Environment secret store]
    end

    Gemini[Google Gemini API\nexternal HTTPS]

    Browser -->|HTTPS| Edge
    Edge --> App
    App -->|private DB connection| PostgreSQL
    App -->|runtime config only| Secrets
    App -->|server-side API call| Gemini
    Worker -.-> App
```

Production deployment must use a managed secret mechanism or equivalent environment
injection. Database and Gemini credentials are not bundled into the frontend artifact or
source control.

## Component diagram

```mermaid
flowchart TB
    subgraph Backend[backend/app]
        Main[main.py\nFastAPI app + handlers]
        Routes[api/routes\nauth, admin, shifts, attendance, reports, assistant]
        Deps[api/deps.py\ncurrent user + role checks]
        Schemas[schemas\nPydantic contracts]
        Services[services\nauth, attendance, reporting, assistant]
        Security[core/security.py\nArgon2 + JWT]
        Config[core/config.py\nsettings]
        Models[models\nUser, Shift, AttendanceRecord, AuditLog]
        DB[db\nengine, session, migrations]
        Tools[assistant tools\nallowlisted read-only functions]
        Masking[assistant privacy\nPII masking + safe fallback]
    end

    Main --> Routes
    Routes --> Deps
    Routes --> Schemas
    Routes --> Services
    Deps --> Security
    Services --> Models
    Services --> DB
    Models --> DB
    Config --> Security
    Services --> Tools
    Tools --> Models
    Services --> Masking
```

The current implementation includes `auth`, admin employee/shift operations, employee
attendance punch/current/history operations, scoped reporting, `security`, settings,
database, models, health routes, and audit service. The assistant module is the next
isolated addition; it will not bypass route-level authorization or the service layer.

## Database ER diagram

```mermaid
erDiagram
    USERS {
        int id PK
        string email UK
        string full_name
        string password_hash
        enum role
        bool is_active
        int shift_id FK
        datetime created_at
        datetime updated_at
    }
    SHIFTS {
        int id PK
        string name UK
        time start_time
        time end_time
        string timezone
        bool is_active
        datetime created_at
    }
    ATTENDANCE_RECORDS {
        int id PK
        int user_id FK
        date work_date
        datetime punch_in_at
        datetime punch_out_at
        datetime created_at
        datetime updated_at
        string user_date_unique UK
    }
    AUDIT_LOGS {
        int id PK
        int actor_user_id FK
        string action
        string entity_type
        string entity_id
        json metadata_json
        string ip_address
        datetime created_at
    }

    SHIFTS ||--o{ USERS : assigns
    USERS ||--o{ ATTENDANCE_RECORDS : owns
    USERS ||--o{ AUDIT_LOGS : creates
```

`ATTENDANCE_RECORDS.user_id + work_date` is unique. `punch_out_at` cannot precede
`punch_in_at`. Shift timezone and work-date rules are deliberately represented in the
domain service rather than relying on database server timezone defaults.

## Authentication sequence

```mermaid
sequenceDiagram
    actor User
    participant UI as React client
    participant API as FastAPI auth route
    participant DB as PostgreSQL
    participant Audit as AuditLog

    User->>UI: Enter email and password
    UI->>API: POST /api/v1/auth/login
    API->>DB: Find active user by normalized email
    API->>API: Verify Argon2 password hash
    alt Credentials valid
        API->>API: Sign short-lived JWT with user ID
        API->>Audit: Record auth.login_succeeded
        API-->>UI: access_token + safe user profile
        UI-->>User: Authenticated application
    else Credentials invalid or inactive
        API->>Audit: Record generic auth.login_failed
        API-->>UI: 401 without account enumeration
        UI-->>User: Generic sign-in error
    end
```

## Punch-in / punch-out sequence (implemented)

```mermaid
sequenceDiagram
    actor Employee
    participant UI as React client
    participant API as FastAPI attendance route
    participant Auth as JWT + employee scope
    participant DB as PostgreSQL transaction
    participant Audit as AuditLog

    Employee->>UI: Select Punch in or Punch out
    UI->>API: POST /api/v1/attendance/punch-in|punch-out
    API->>Auth: Validate token, active user, and employee scope
    Auth-->>API: Authorized employee identity
    API->>DB: Begin transaction; lock/find employee work-date row
    alt Punch-in and no existing punch-in
        API->>DB: Insert record with UTC timestamp
        DB-->>API: Commit
        API->>Audit: Record attendance.punch_in
        API-->>UI: Updated attendance state
    else Punch-out after valid punch-in and no punch-out
        API->>DB: Update row with UTC timestamp
        DB-->>API: Commit
        API->>Audit: Record attendance.punch_out
        API-->>UI: Updated attendance state
    else Duplicate or invalid transition
        API-->>UI: 409/422 structured error; no data mutation
    end
```

The service and database constraint both protect against duplicate actions. A client-side
button state is not an authorization or integrity control.

## AI attendance query sequence (planned)

```mermaid
sequenceDiagram
    actor User
    participant UI as React assistant UI
    participant API as FastAPI assistant route
    participant Auth as JWT/RBAC + data scope
    participant Intent as Intent/tool validator
    participant Tool as Read-only report tool
    participant DB as PostgreSQL
    participant Gemini as Gemini API
    participant Mask as PII masker

    User->>UI: Ask natural-language attendance question
    UI->>API: POST /api/v1/assistant/query
    API->>Auth: Validate token, role, and employee scope
    API->>Intent: Parse request and allow only known tool names/arguments
    Intent->>Tool: Call validated report function
    Tool->>DB: Parameterized query with server-side scope
    DB-->>Tool: Scoped report data only
    Tool-->>Intent: Structured report result
    Intent->>Gemini: Send bounded context, never SQL or secrets
    alt Gemini available and response passes policy
        Gemini-->>Mask: Draft answer
        Mask-->>API: PII-masked response
        API-->>UI: Answer + report metadata
    else Gemini unavailable or unsafe response
        API-->>UI: Deterministic fallback using verified report data
    end
```

The model cannot execute arbitrary SQL. If a tool name or argument is not allowlisted,
the API rejects it. Authorization and employee scoping happen before any report result is
returned, and logs/responses must mask applicable PII.
