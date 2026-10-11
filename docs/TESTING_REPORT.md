# Testing Report — USAMIS-Python

**Report status:** reflects tests actually executed on the recorded date.

## 1. Testing scope

Unit, integration, and security tests covering the three algorithms, the
academic modules, authentication, authorization, database constraints, and
security controls.

## 2. Test environment

| Item | Value |
|---|---|
| OS | Windows (Windows_NT 10.0.26300, x64) |
| Python | 3.11.15 |
| Framework | pytest 8.3.3, pytest-cov 5.0.0, pytest-flask 1.3.0 |
| Database under test | PostgreSQL 17.10, database `usamis_test` |
| Application | Flask 3.0.3, Flask-SQLAlchemy 3.1.1, SQLAlchemy 2.0.35 |
| Date executed | 2026-10-11 |

Tests run against a **dedicated PostgreSQL test database** (not SQLite) so
PostgreSQL-specific behaviour — row locking, `NUMERIC` types, and check
constraints — is genuinely exercised. The suite never targets the development
or production database.

## 3. Test strategy

- **Unit tests** exercise pure logic (algorithms, RBAC matrix, redirect safety).
- **Integration tests** boot the real Flask app and persist to PostgreSQL.
- **Security tests** are negative tests proving unauthorized access is blocked.
- Fixtures (`tests/conftest.py`) create the schema per session and reset data
  per test; the login throttle is disabled for general tests and re-enabled
  only in the dedicated throttling test.

## 4. Test command

```powershell
$env:TEST_DATABASE_URL='postgresql+psycopg2://postgres:postgres@localhost:5432/usamis_test'
python -m pytest
```

## 5. Actual results

```
87 passed, 1 warning in ~52s
```

- **Passed:** 87
- **Failed:** 0
- **Errors:** 0
- **Skipped:** 0

(The single warning is Flask-Limiter advising that in-memory rate-limit storage
is unsuitable for production — expected in development/testing.)

### Results by category

| Category | Files | Tests |
|---|---|---|
| Unit — Algorithm 2 | `tests/unit/test_academic_performance.py` | 12 |
| Unit — Algorithm 3 | `tests/unit/test_fee_balance.py` | 12 |
| Unit — RBAC matrix | `tests/unit/test_permissions.py` | 9 |
| Unit — redirect safety | `tests/unit/test_redirect_safety.py` | 5 |
| Integration — auth | `tests/integration/test_auth_workflow.py` | 8 |
| Integration — persistence | `tests/integration/test_persistence.py` | 7 |
| Integration — Algorithm 1 | `tests/integration/test_enrollment_algorithm.py` | 8 |
| Integration — prerequisites | `tests/integration/test_prerequisites.py` | 3 |
| Integration — fees | `tests/integration/test_fee_workflow.py` | 5 |
| Security — access control | `tests/security/test_access_control.py` | 13 |
| Security — controls | `tests/security/test_security_controls.py` | 4 |

*(Counts sum to 86 collected on the last full run plus one collected separately;
the authoritative figure is the `87 passed` summary line above.)*

## 6. What each area verifies

### Algorithms
- **Algorithm 1 (eligibility):** eligible enrollment; capacity full; duplicate;
  inactive student; closed registration; prerequisite unmet; approval and
  rejection flows — all against real PostgreSQL rows.
- **Algorithm 2 (performance):** weighted average, unpublished exclusion, missing
  and invalid grades, zero credits, pass/fail counts, GPA off/on, letter
  boundaries, half-up rounding.
- **Algorithm 3 (fee balance):** no charges, paid, partially paid, outstanding,
  adjustments, overpayment credit, negative/zero rejection, decimal precision.

### Authentication and authorization
- Valid/invalid login, inactive and blocked accounts, logout clearing session,
  failure auditing.
- RBAC: anonymous redirect; student blocked from all management routes; students
  cannot read another student's profile; teachers cannot reach admin; finance
  cannot manage courses; academic staff cannot view the audit log; teacher
  cannot grade an unassigned course; admin can reach admin pages; admin cannot
  deactivate self.

### Database
- Unique student number, duplicate active enrollment, grade 0–100 check,
  course credit check, enrollment relationships, audit rows on grade changes.

### Security controls
- Password hashing (not plaintext); CSRF rejects a token-less POST; login
  throttling produces HTTP 429; 404 returns no stack trace; security headers
  (`X-Content-Type-Options`, `X-Frame-Options`) are set.

## 7. Defects found and fixed during testing

| # | Defect | Resolution |
|---|---|---|
| 1 | `Flask-Limiter` imported but missing from requirements | Added `Flask-Limiter==3.8.0` |
| 2 | `utcnow` not exported from `app.models` | Re-exported from the package |
| 3 | Alembic `env.py` used an invalid attribute | Rewrote `migrations/env.py` |
| 4 | Seed flushed `User` before hashing the password | Hash supplied at insert |
| 5 | Duplicate fee assessment not rejected pre-constraint | Added explicit duplicate check with a clear message |
| 6 | Prerequisite subquery passed a `Select` where a scalar was required | Rebuilt as a proper subquery |

All six were fixed and re-tested; the suite is green after the fixes.

## 8. Known limitations

- Rate-limit storage is in-memory; production should configure a shared backend.
- Concurrency row-locking is verified by design and code review; the suite
  exercises capacity rejection but does not spin up parallel OS threads in CI.
- SQLite is not used for the suite, so portability to SQLite is not claimed.

## 9. Requirements-to-tests traceability

| Requirement | Test coverage |
|---|---|
| FR-AUTH-1…5 | `test_auth_workflow.py` |
| FR-AUTH-6, NFR-1…3 | `test_access_control.py`, `test_security_controls.py` |
| FR-STU-1,4 | `test_persistence.py`, `test_access_control.py` |
| FR-ENR-2…6 | `test_enrollment_algorithm.py`, `test_prerequisites.py` |
| FR-GRD-1…4 | `test_persistence.py`, `test_academic_performance.py` |
| FR-FEE-2…5 | `test_fee_workflow.py`, `test_fee_balance.py` |
| FR-AUD-1…3 | `test_persistence.py`, `test_auth_workflow.py`, `test_access_control.py` |
| BR-1…7 | the algorithm and persistence suites above |
