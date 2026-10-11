# USAMIS-Python

**University Student Academic Management Information System**

A role-based Management Information System (MIS) for university academic
administration, built with **Python, Flask, SQLAlchemy, and PostgreSQL**.

---

## Overview

USAMIS centralises student academic administration: student records, academic
structure (departments, programs, courses, semesters), course enrollment,
grades, attendance, fees, and management reporting. Authorization is enforced
**on the server** for every protected operation, and sensitive actions are
recorded in an audit log.

The system includes **three explainable, deterministic algorithms** (not AI/ML):

1. **Course Enrollment Eligibility** — status, duplicates, prerequisites, capacity.
2. **Academic Performance** — credit-weighted average of published grades.
3. **Fee Balance & Payment Status** — decimal-safe balance with status rules.

## Roles

| Role | Capabilities |
|---|---|
| Administrator | Full control; user management; audit-log review |
| Academic staff / Registrar | Students, departments, programs, courses, semesters, enrollment |
| Teacher | Grades and attendance for assigned courses |
| Finance officer | Fee assessments, payments, balances |
| Student | Own profile, enrollment, grades, attendance, fees |

## Technology

Python 3.11 · Flask · SQLAlchemy 2.0 · Flask-Migrate/Alembic · Flask-Login ·
Flask-WTF · Flask-Limiter · PostgreSQL · HTML5/CSS3/vanilla JS · pytest.

## Quick start

```powershell
# 1. Virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt

# 3. Databases
$env:PGPASSWORD='postgres'
& "D:\postgresql\bin\psql.exe" -U postgres -h localhost -c "CREATE DATABASE usamis_dev;"
& "D:\postgresql\bin\psql.exe" -U postgres -h localhost -c "CREATE DATABASE usamis_test;"

# 4. Configuration
Copy-Item .env.example .env      # then edit SECRET_KEY and DATABASE_URL

# 5. Schema + demo data
$env:FLASK_APP='wsgi.py'
python -m flask db upgrade
python -m flask seed

# 6. Run
python run.py                    # http://127.0.0.1:5000

# 7. Test
$env:TEST_DATABASE_URL='postgresql+psycopg2://postgres:postgres@localhost:5432/usamis_test'
python -m pytest
```

Full instructions: **`docs/INSTALLATION_GUIDE.md`**.

## Demo accounts (development only)

| Username | Role | Password |
|---|---|---|
| `admin` | Administrator | `Demo_Pass1!` |
| `registrar` | Academic staff | `Demo_Pass1!` |
| `t.mensah` | Teacher | `Demo_Pass1!` |
| `finance` | Finance officer | `Demo_Pass1!` |
| `s.demo` | Student | `Demo_Pass1!` |

Change these before any shared or production use.

## Project structure

```
USAMIS-PROJECT-Python-/
├── app/
│   ├── __init__.py          # application factory
│   ├── config.py            # development / testing / production
│   ├── extensions.py        # db, migrate, login, csrf, limiter
│   ├── models/              # SQLAlchemy models
│   ├── security/            # RBAC matrix + decorators
│   ├── services/            # audit, enrollment, grade, fee
│   ├── algorithms/          # the three algorithms
│   ├── auth|dashboard|students|departments|programs|courses|
│   │   semesters|enrollments|grades|attendance|fees|reports|admin/
│   ├── templates/           # Jinja2 templates
│   └── static/              # css, js, images
├── migrations/              # Alembic revisions
├── tests/                   # unit / integration / security
├── docs/                    # SRS, reports, guides, diagrams, PPTX
├── scripts/                 # smoke test, PPTX generation/verification
├── .env.example
├── requirements.txt / requirements-dev.txt
├── pyproject.toml
├── pytest.ini
├── wsgi.py / run.py
└── README.md
```

## Documentation

| Document | Path |
|---|---|
| Software Requirements Specification | `docs/SRS.md` |
| Project report | `docs/PROJECT_REPORT.md` |
| Architecture | `docs/ARCHITECTURE.md` |
| Database design | `docs/DATABASE_DESIGN.md` |
| Algorithms | `docs/ALGORITHMS.md` |
| Installation guide | `docs/INSTALLATION_GUIDE.md` |
| User manual | `docs/USER_MANUAL.md` |
| Testing report | `docs/TESTING_REPORT.md` |
| Project status | `docs/PROJECT_STATUS.md` |
| Presentation | `docs/USAMIS_Presentation.pptx` |
| Five diagrams (source + PNG) | `docs/diagrams/` |

## Security highlights

- Passwords stored as salted hashes (Werkzeug).
- CSRF protection on state-changing forms.
- Server-side RBAC and ownership checks on every protected route.
- Login throttling plus account lockout after repeated failures.
- Parameterized ORM queries only.
- Security headers; error pages reveal no stack traces.
- Audit log of sensitive actions.

## License

See `LICENSE`.
