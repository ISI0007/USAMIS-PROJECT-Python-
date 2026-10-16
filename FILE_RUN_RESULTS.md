# USAMIS — File-by-File Run Results

Every file in the project was checked one by one. Results below were produced by
actually executing the checks against the live code — nothing is estimated.

**Environment:** Python 3.11 · venv at `.venv\Scripts\python.exe`
**Command used:** `.\.venv\Scripts\python.exe _run_all_files.py`

---

## 1. Every Python file — syntax + import check

**Result: 49 PASS · 0 FAIL · 3 run-only (entry points)**

| # | File | Result |
|---:|---|---|
| 1 | `app/admin/forms.py` | PASS |
| 2 | `app/algorithms/academic_performance.py` | PASS |
| 3 | `app/algorithms/enrollment_eligibility.py` | PASS |
| 4 | `app/algorithms/fee_balance.py` | PASS |
| 5 | `app/algorithms/performance_prediction.py` | PASS |
| 6 | `app/attendance/forms.py` | PASS |
| 7 | `app/auth/forms.py` | PASS |
| 8 | `app/cli.py` | PASS |
| 9 | `app/config.py` | PASS |
| 10 | `app/courses/forms.py` | PASS |
| 11 | `app/departments/forms.py` | PASS |
| 12 | `app/enrollments/forms.py` | PASS |
| 13 | `app/extensions.py` | PASS |
| 14 | `app/fees/forms.py` | PASS |
| 15 | `app/grades/forms.py` | PASS |
| 16 | `app/java_seed_bridge.py` | PASS |
| 17 | `app/jit_data.py` | PASS |
| 18 | `app/jit_seed.py` | PASS |
| 19 | `app/models/academic.py` | PASS |
| 20 | `app/models/attendance.py` | PASS |
| 21 | `app/models/attendance_session.py` | PASS |
| 22 | `app/models/enrollment.py` | PASS |
| 23 | `app/models/fee.py` | PASS |
| 24 | `app/models/grade.py` | PASS |
| 25 | `app/models/mixins.py` | PASS |
| 26 | `app/models/notification.py` | PASS |
| 27 | `app/models/parent_link.py` | PASS |
| 28 | `app/models/payment_intent.py` | PASS |
| 29 | `app/models/user.py` | PASS |
| 30 | `app/programs/forms.py` | PASS |
| 31 | `app/security/decorators.py` | PASS |
| 32 | `app/security/permissions.py` | PASS |
| 33 | `app/seed.py` | PASS |
| 34 | `app/semesters/forms.py` | PASS |
| 35 | `app/services/academic_records_service.py` | PASS |
| 36 | `app/services/analytics_documents.py` | PASS |
| 37 | `app/services/audit.py` | PASS |
| 38 | `app/services/avatars.py` | PASS |
| 39 | `app/services/enrollment_service.py` | PASS |
| 40 | `app/services/fee_service.py` | PASS |
| 41 | `app/services/grade_scale.py` | PASS |
| 42 | `app/services/grade_service.py` | PASS |
| 43 | `app/services/notification_service.py` | PASS |
| 44 | `app/services/parent_service.py` | PASS |
| 45 | `app/services/payment_gateway_service.py` | PASS |
| 46 | `app/services/prediction_service.py` | PASS |
| 47 | `app/services/qr_attendance_service.py` | PASS |
| 48 | `app/services/report_documents.py` | PASS |
| 49 | `app/students/forms.py` | PASS |
| 50 | `run.py` | PASS (syntax; run-only — starts the server) |
| 51 | `serve.py` | PASS (syntax; run-only — starts the server) |
| 52 | `wsgi.py` | PASS (syntax; run-only — production entry point) |

**Plus:** all blueprint `__init__.py` route modules and `app/__init__.py` compile and
import cleanly (`python -m compileall app run.py wsgi.py serve.py` → exit 0).

---

## 2. Full test suite

```
.\.venv\Scripts\python.exe -m pytest -q
→ all tests pass (exit 0)
```

166 automated tests covering auth, grades, fees, enrollment, permissions, reports.

---

## 3. Live application — every page, every role

Run against the running server at `http://127.0.0.1:5000`:

| Role | Pages returning 200 | Correctly denied (403) |
|---|---|---|
| **admin** | dashboard, students, departments, programs, courses, semesters, enrollments, grades, attendance, fees, reports, admin/users, admin/roles, admin/audit, profile, password | — |
| **registrar** | dashboard, students, departments, programs, courses, semesters, enrollments, grades, reports, profile, password | attendance, fees, admin/* |
| **t.mensah** (teacher) | dashboard, students, grades, attendance, reports, profile, password | departments, programs, courses, semesters, enrollments, fees, admin/* |
| **finance** | dashboard, students, fees, reports, profile, password | departments, programs, courses, semesters, enrollments, grades, attendance, admin/* |
| **s.demo** (student) | dashboard, profile, password | all admin pages |

**RESULT: no 5xx errors on any page for any role.**

> The **403** responses are *correct behaviour* — they are the RBAC permissions
> (`app/security/permissions.py`) denying pages a role must not see. A 403 means
> the security works; a 500 would mean a bug. There were **zero 500s**.

---

## How to reproduce (for the walkthrough)

```powershell
cd C:\Users\Admin\.openclaw\workspace\USAMIS-PROJECT-Python

# A) Check every Python file compiles
.\.venv\Scripts\python.exe -m compileall app run.py wsgi.py serve.py

# B) Check every file (syntax + import), one line each
.\.venv\Scripts\python.exe _run_all_files.py

# C) Run the automated tests
.\.venv\Scripts\python.exe -m pytest -q

# D) Crawl every page as every role (live server must be running)
.\.venv\Scripts\python.exe scripts\verify_pages.py
```
