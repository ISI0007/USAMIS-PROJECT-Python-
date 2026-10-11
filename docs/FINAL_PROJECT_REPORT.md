# USAMIS-Python — Final Project Report

**Project:** University Student Academic Management Information System (USAMIS)
**Stack:** Python 3.11 · Flask · SQLAlchemy · PostgreSQL 17 · Alembic · pytest
**Repository:** https://github.com/ISI0007/USAMIS-PROJECT-Python-
**Report date:** 2026-10-12
**Status:** Implemented, tested, documented, and verified on this machine.

---

## 1. Executive summary

USAMIS-Python is a role-based academic management information system for a
university. It manages departments, academic programmes, students, teachers,
courses, prerequisites, semesters, course offerings, enrollment (with
eligibility checking), grades, attendance, fees/payments, and reporting.

The application is built with the Flask application-factory pattern, enforces
authorization **server-side** through a single permission matrix, and stores
data in PostgreSQL via SQLAlchemy models managed by Alembic migrations. It is
covered by an automated test suite and ships with a full set of academic
deliverables (SRS, architecture, database design, algorithms, installation
guide, user manual, testing report, project report, five diagrams, real
application screenshots, and a 15-slide presentation).

### Current verification on this machine (2026-10-12)

| Check | Result |
|---|---|
| Automated tests (PostgreSQL `usamis_test`) | **87 passed, 0 failed** |
| Fresh-database migration | **PASS** — 17 tables created |
| Role/route RBAC checks | **70 / 70 pass** |
| Per-role navigation checks | **PASS** — nav matches permission matrix |
| App screenshots captured | **16 / 16**, all distinct, valid PNGs |
| Enrollment DB-level integrity | **PASS** — partial unique index enforced |
| Presentation file | **PASS** — OOXML valid, 15 slides |
| Diagram exports | **PASS** — 5 PNGs, valid signatures |
| Live application | **Running** at http://127.0.0.1:5000 |

---

## 2. What was built

### 2.1 Architecture

- **Application factory** (`app/__init__.py`) with per-environment configuration
  (development / testing / production) selected via `FLASK_ENV`.
- **13 feature blueprints:** auth, dashboard, students, departments, programs,
  courses, semesters, enrollments, grades, attendance, fees, reports, admin.
- **Service layer** for cross-cutting business actions (audit, enrollment,
  grades, fees) so blueprints stay thin.
- **16 SQLAlchemy models** with timestamp mixins and DB-level constraints.
- **Central RBAC** in `app/security/permissions.py` — the permission matrix is
  the single source of truth used by decorators, templates, and tests.

### 2.2 Roles and permissions

Five roles: **administrator, academic staff, teacher, finance, student**.
Authorization is enforced on the backend; the sidebar merely hides what a role
cannot use. Verified per role (see §5).

### 2.3 Three explainable algorithms

1. **Enrollment eligibility** (`app/algorithms/enrollment_eligibility.py`) —
   checks registration window, prerequisites, duplicates, and capacity.
2. **Academic performance** (`app/algorithms/academic_performance.py`) —
   computes averages/GPA from **published** grades only (GPA gate controlled by
   `GPA_ENABLED`).
3. **Fee balance** (`app/algorithms/fee_balance.py`) — Decimal-safe outstanding
   balance = assessments + adjustments − payments.

Each algorithm is documented in `docs/ALGORITHMS.md` with its inputs, rules, and
worked examples, and each has dedicated unit tests.

### 2.4 Database

PostgreSQL, managed by Alembic. Migrations:

| Revision | Description |
|---|---|
| `a5dbe550ba23` | Initial schema (17 tables) |
| `b7c1a5f0d9e2` | Partial unique index for active enrollments (see §6.1) |

---

## 3. Seed data (realistic, curriculum-based)

The demo dataset models a real 4-year / 8-semester Software Engineering
programme.

- **Departments:** Software Engineering (0809), General Education (0501),
  Physical Education (0402).
- **Programme:** BSc Software Engineering, 137 credits, 4 years.
- **Courses:** 44 courses across 8 semesters, using the real course codes and
  titles from the programme curriculum (e.g. `080931201L` Advanced Language
  Programming, `080931205L` Data Structures and Algorithms, `080991207L`
  Graduation Thesis).
- **Prerequisites:** 7 realistic chains, e.g. Data Structures → Operating
  Systems; Introduction to Software Engineering → Software Architecture /
  Software Testing / Web Development.
- **Semesters:** 8 (2024/25 → 2027/28), fall/spring.
- **Students:** roll numbers following the institutional pattern
  `G + 22 + 2486 + 0 + NN`:

  | Roll | Student | Email |
  |---|---|---|
  | G2422486019 | Lin Wei | g2422486019@usamis.demo |
  | G2422486020 | Chen Yu | g2422486020@usamis.demo |
  | G2422486021 | Zhang Hao | g2422486021@usamis.demo |
  | G2422486022 | Wang Fang | g2422486022@usamis.demo |
  | G2422486023 | Liu Yang | g2422486023@usamis.demo |
  | G2422486024 | Zhao Min | g2422486024@usamis.demo |
  | G2422486025 | Sun Lei | g2422486025@usamis.demo |
  | G2422486026 | Zhou Xin | g2422486026@usamis.demo |

- **Enrollments / grades / attendance / fees** generated deterministically for
  the cohort; fee categories include Tuition (12,000), Library (300), and
  Accommodation (1,200).

Seeding is **idempotent** (`flask seed`) and supports `--reset` for a clean
rebuild.

---

## 4. Features delivered

| Module | Capability |
|---|---|
| Authentication | Login, logout, self-registration, password change, profile |
| RBAC | Five roles; server-side enforcement; lockout after repeated failures |
| Students | CRUD, profiles, department/programme assignment |
| Academic structure | Departments, programmes, courses, prerequisites, semesters |
| Offerings | Course offerings per semester with teacher and capacity |
| Enrollment | Eligibility-checked requests, approval, capacity, prerequisites |
| Grades | Entry, publication gate, letter mapping, per-student views |
| Attendance | Recording and per-student views |
| Fees | Categories, assessments, payments, Decimal-safe balances |
| Reports | Enrollment, grades, attendance, fee defaulters |
| Administration | User management, role overview, audit log |
| Public registration | New accounts default to the **student** role |

---

## 5. Verification evidence

### 5.1 Automated tests

Command: `python -m pytest` against PostgreSQL `usamis_test`.
Result: **87 passed, 0 failed** (1 non-blocking Flask-Limiter storage warning).

Coverage spans unit tests (all three algorithms), integration tests (auth,
enrollment, grade, fee workflows), and security tests (RBAC enforcement).

### 5.2 Role / route authorization — 70 checks

`scripts/verify_features.py` logs in as each demo account and probes every
module route, asserting the expected allow/deny result. Result: **all 70 checks
behaved as expected.**

### 5.3 Per-role navigation — matches the matrix

`scripts/verify_ui.py` inspects each role's rendered sidebar and confirms it
shows exactly the modules that role may access:

| Role | Visible modules |
|---|---|
| administrator | Dashboard, Students, Departments, Programs, Courses, Semesters, Enrollments, Grades, Attendance, Fees, Reports, Users, Roles, Audit |
| academic_staff | Dashboard, Students, Departments, Programs, Courses, Semesters, Enrollments, Grades, Reports |
| teacher | Dashboard, Students, Grade Entry, Attendance, Reports |
| finance | Dashboard, Students, Fees, Reports |
| student | Dashboard, My Enrollments, Enroll in Course, My Grades, My Attendance, My Fees |

### 5.4 Screenshots

`docs/screenshots/` contains **16 real captures** of the running application
produced by `scripts/capture_screenshots.py` (Playwright/Chromium). All 16 files
have distinct content hashes and valid PNG signatures — they are genuine
renders, not mock-ups.

### 5.5 Fresh-database reproducibility

A fresh database was created, migrated from scratch (`flask db upgrade`), and
inspected: **17 tables** present. Combined with the idempotent seed, the project
reproduces from an empty database.

---

## 6. Findings addressed during this cycle

### 6.1 Enrollment integrity hardened at the database level (audit finding #3)

**Problem:** the constraint `UNIQUE(student_id, offering_id, status)` still
allowed one `pending` and one `enrolled` row for the same student/offering — the
business rule was only enforced in application code.

**Fix:** added a PostgreSQL **partial unique index**
`uq_active_enrollment_student_offering` over `(student_id, offering_id)`
restricted to active statuses (`pending`, `enrolled`, `completed`), delivered via
migration `b7c1a5f0d9e2`. Rejected/dropped rows are retained as history.

**Verification:** the index exists in PostgreSQL and a deliberate duplicate
`pending` insert is now rejected with a `UniqueViolation` at the database layer.

### 6.2 RBAC over-permission corrected

Teachers and finance could reach `/courses/` and `/semesters/` because the
guards (and the sidebar) used `manage_courses OR view_students`. Tightened to
the documented `manage_*` permissions. Verified: 70/70 route checks pass and
navigation matches per role.

### 6.3 Sidebar showed student self-service links to administrators

"My Enrollments / My Grades / My Attendance / My Fees" rendered for the
administrator. Now restricted to the student role.

### 6.4 Sign-in failure diagnosed correctly

An apparent login failure was traced to the **account-lockout control working as
designed** (the demo accounts had accumulated failed attempts during automated
probing). This is recorded as evidence the lockout feature functions, and the
lock state is now cleared during test/utility runs.

### 6.5 Course credit range widened

The model capped credits at 12, but the real curriculum includes a 15-credit
Graduation Thesis. The constraint (and the database) now allow up to 20.

---

## 7. Outstanding items (honest status)

These remain and are **not** claimed as done:

1. **CI automation** — no GitHub Actions workflow yet. There is no automated
   pipeline running the suite against a PostgreSQL service. The audit's
   recommendation stands.
2. **Shared rate-limit backend** — Flask-Limiter uses in-memory storage; suitable
   for dev/test, not multi-worker production. A Redis backend is recommended.
3. **Production secret/DB validation** — production config should fail fast if
   `SECRET_KEY` or `DATABASE_URL` is missing rather than falling back to dev
   defaults.
4. **POST-only logout** — `/auth/logout` currently accepts GET as well as POST.
5. **Proxy-aware audit IP** — `X-Forwarded-For` is trusted directly; should be
   gated behind trusted-proxy configuration.
6. **Additional data validation** at the DB level (e.g. `adjustment <= amount`,
   semester date ordering, prerequisite grade range).
7. **Deeper test breadth** — lockout-expiry, password-change session, and
   full browser end-to-end tests per role.

---

## 8. Reproducing the project

```powershell
# 1. Environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt

# 2. Configuration
Copy-Item .env.example .env      # then edit SECRET_KEY and DATABASE_URL

# 3. Database
#    create usamis_dev and usamis_test, then:
$env:FLASK_APP = 'wsgi.py'
python -m flask db upgrade
python -m flask seed             # or: python -m flask seed --reset

# 4. Run
python run.py                    # http://127.0.0.1:5000

# 5. Verify
python -m pytest                 # 87 tests
python scripts/verify_features.py
python scripts/verify_ui.py
python scripts/capture_screenshots.py   # requires: python -m playwright install chromium
```

### Demo accounts (development only — password `Demo_Pass1!` for all)

| Role | Username |
|---|---|
| Administrator | `admin` |
| Academic staff | `registrar` |
| Teacher | `t.mensah` |
| Finance officer | `finance` |
| Student | `s.demo` |

> **Security note:** these credentials are printed on the login page for demo
> convenience. Remove the demo panel and change all credentials before any
> shared or production deployment. The `.env` file is gitignored.

---

## 9. Deliverables index

| Deliverable | Path |
|---|---|
| SRS | `docs/SRS.md` |
| Architecture | `docs/ARCHITECTURE.md` |
| Database design | `docs/DATABASE_DESIGN.md` |
| Algorithms | `docs/ALGORITHMS.md` |
| Installation guide | `docs/INSTALLATION_GUIDE.md` |
| User manual | `docs/USER_MANUAL.md` |
| Testing report | `docs/TESTING_REPORT.md` |
| Project report | `docs/PROJECT_REPORT.md` |
| Project status / DoD | `docs/PROJECT_STATUS.md` |
| Diagrams (5) | `docs/diagrams/*.mmd`, `*.png` |
| Screenshots (16) | `docs/screenshots/*.png` |
| Presentation | `docs/USAMIS_Presentation.pptx` |

---

## 10. Conclusion

USAMIS-Python is a complete, working academic management information system. On
this machine it migrates from an empty database, seeds a realistic 8-semester
curriculum with the G19–G26 cohort, passes all 87 automated tests on PostgreSQL,
enforces role-based access correctly on both routes and navigation, enforces
enrollment integrity at the database level, and provides a full set of academic
deliverables including real application screenshots and a valid presentation.

The remaining work is **production-hardening and CI** rather than feature
completeness: a GitHub Actions pipeline with a PostgreSQL service, a shared
rate-limit backend, fail-fast production configuration, POST-only logout, and
proxy-aware audit logging. These are enumerated in §7 and are the natural next
milestone.
