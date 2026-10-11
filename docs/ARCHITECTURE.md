# Architecture — USAMIS-Python

## 1. Overview

USAMIS-Python is a layered Flask web application following the
application-factory pattern. Concerns are separated into presentation,
application (blueprints + services + algorithms), and data (SQLAlchemy +
PostgreSQL) tiers.

```
Browser (HTML5 / CSS3 / vanilla JS)
        │  HTTPS
Flask application factory  (app/__init__.py)
   ├── blueprints (feature routes)
   ├── security  (RBAC matrix + decorators)
   ├── services  (business rules, transactions, auditing)
   ├── algorithms (pure, deterministic)
   └── models    (SQLAlchemy 2.0 declarative)
        │  parameterized ORM
PostgreSQL 17
```

## 2. Application factory

`create_app(config_name=None, config_object=None)` builds the app in explicit
steps: configuration → extensions → blueprints → error handlers → security
headers → CLI. Passing `config_object` lets tests inject a configuration
without touching the environment.

Key files: `app/__init__.py`, `app/config.py`, `app/extensions.py`.

## 3. Blueprint organisation

| Blueprint | URL prefix | Responsibility |
|---|---|---|
| `auth` | `/auth` | login, logout, profile, password |
| `dashboard` | `/dashboard` | role-specific dashboards |
| `students` | `/students` | student CRUD, profiles |
| `departments` | `/departments` | department management |
| `programs` | `/programs` | academic program management |
| `courses` | `/courses` | course catalogue, prerequisites |
| `semesters` | `/semesters` | semesters and offerings |
| `enrollments` | `/enrollments` | requests, approvals, history |
| `grades` | `/grades` | grade entry, publication, own grades |
| `attendance` | `/attendance` | attendance recording and views |
| `fees` | `/fees` | categories, assessments, payments |
| `reports` | `/reports` | management reports |
| `admin` | `/admin` | users, roles, audit log |

## 4. Service layer

Route handlers validate input and delegate to services. This keeps business
rules reusable and testable.

- `services/audit.py` — single entry point for audit writes (actor/IP captured
  from the request; never stores secrets).
- `services/enrollment_service.py` — wraps Algorithm 1 with transaction and
  row-lock handling.
- `services/grade_service.py` — grade entry, publication, authorization of the
  assigned teacher, change auditing.
- `services/fee_service.py` — assessments, payments, balance computation via
  Algorithm 3.

## 5. Algorithm modules

Algorithms live in `app/algorithms/` and are pure enough to unit-test without
the web layer:

- `enrollment_eligibility.py` — Algorithm 1.
- `academic_performance.py` — Algorithm 2.
- `fee_balance.py` — Algorithm 3.

They import models only where a database read is required (Algorithm 1); the
performance and fee algorithms are pure functions over plain inputs.

## 6. ORM and database access

SQLAlchemy 2.0 declarative models (`app/models/`) with explicit relationships,
check constraints, and unique constraints. All queries use the ORM/parameter
binding — no string-concatenated SQL. Multi-step operations use transactions;
capacity checks use `SELECT … FOR UPDATE`.

## 7. Authentication and authorization

- Authentication: Flask-Login + Werkzeug password hashing.
- Authorization: a single permission matrix (`app/security/permissions.py`)
  with `permission_required` / `roles_required` decorators.
- Ownership: student-facing routes re-derive the current student from the
  session and reject access to other students' identifiers.
- Throttling: Flask-Limiter on the login POST, plus account lockout after
  repeated failures.

## 8. Algorithm integration

| Algorithm | Called from | Effect |
|---|---|---|
| 1 Eligibility | `enrollment_service.request_enrollment` | accepts/rejects a request |
| 2 Performance | `dashboard`, `grades.my_grades` | weighted average / optional GPA |
| 3 Fee balance | `fee_service.student_balance`, dashboards | balance and status |

## 9. Error handling

- `403` — authenticated but unauthorized.
- `404` — missing resource.
- `500` — unexpected error (session rolled back; no stack trace to the client).
- `401` — anonymous access to a protected endpoint (redirected to login).

Flash messages convey validation and business-rule failures.

## 10. Deployment model

Development uses `run.py` / `flask run`. Production must use a WSGI server
(e.g. gunicorn or waitress) behind a TLS-terminating reverse proxy, with
`FLASK_ENV=production`, `SESSION_COOKIE_SECURE=true`, and a strong
`SECRET_KEY`. The Flask development server must not be used in production.

## 11. Major design decisions

1. **Application factory** — clean test isolation and multiple configs.
2. **Single RBAC matrix** — one source of truth for permissions.
3. **Services over fat routes** — reuse and testability.
4. **Pure algorithms** — deterministic, documented, unit-tested, non-AI.
5. **Explicit grade publication** — avoids leaking provisional marks.
6. **Decimal money** — avoids floating-point rounding errors.
7. **Row locking for capacity** — correctness under concurrent enrollment.
8. **Soft deactivation** — preserves academic history.
