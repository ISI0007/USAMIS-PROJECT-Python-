# Software Requirements Specification — USAMIS-Python

**University Student Academic Management Information System**

| Field | Value |
|---|---|
| Project | USAMIS-Python |
| Version | 1.0 |
| Document type | Software Requirements Specification (IEEE-style) |
| Repository | https://github.com/ISI0007/USAMIS-PROJECT-Python- |
| Technology | Python 3.11, Flask, SQLAlchemy, PostgreSQL 17 |
| Status | Implemented and tested (see `docs/TESTING_REPORT.md`) |

---

## 1. Purpose and scope

This document specifies the requirements for USAMIS-Python, a role-based
Management Information System (MIS) for university student academic
administration. It covers authentication, student and academic-structure
management, enrollment, grades, attendance, fees, reporting, and audit
logging.

The scope is a demonstrable, testable academic MIS. It does **not** include
real online payment processing, an admissions portal, or AI/ML features (three
conventional, explainable algorithms are specified instead).

 > Planned extension: SMS notifications, an online payment gateway, QR-code
 > attendance, AI-based performance prediction, and a parent portal are being
 > added as a follow-on release (full implementation, with external providers
 > behind adapter interfaces using offline development stubs). See
 > `docs/EXPANSION_PLAN.md`.

### 1.1 How USAMIS solves academic management problems

USAMIS addresses the day-to-day problems of academic administration by treating
them as a single system built on **people, process, and technology** that turns
raw records into **information** for **decisions**.

| Dimension | How USAMIS delivers it |
|---|---|
| **People** | Every stakeholder (student, teacher, registrar, finance, administrator, parent) gets a role-scoped view and the exact actions their job requires — nothing more, nothing less. |
| **Process** | The academic lifecycle runs as one flow: admit student → register/enroll → teach → grade → record attendance → assess and pay fees → report. |
| **Technology** | Python Flask + SQLAlchemy on PostgreSQL 17, with server-side authorization, database constraints, and full audit logging. |
| **Information** | Live records become management information: enrollment trends, grade distributions, attendance rates, and fee-collection status. |
| **Decisions** | Real-time reports give administrators evidence for staffing, intervention, and finance decisions. |

**Concrete value provided:**

- **Centralized data management** — removes scattered, paper and spreadsheet records in favour of one authoritative relational database.
- **Secure, role-based access control** — enforces data integrity and confidentiality; every protected operation is authorized server-side.
- **Reliable data storage** — PostgreSQL 17 with transactional integrity, constraints, and migrations.
- **Flexible, scalable backend** — Python Flask with a modular blueprint architecture.
- **Comprehensive functionality** — full add / edit / delete / view operations across every module, with a complete audit trail.
- **Real-time management reports** — derived from live data for informed decision-making.

## 2. Definitions and abbreviations

| Term | Meaning |
|---|---|
| MIS | Management Information System |
| RBAC | Role-Based Access Control |
| SRS | Software Requirements Specification |
| USAMIS | University Student Academic Management Information System |
| Offering | A course taught in a specific semester by a specific teacher |
| Registered user | An authenticated account with exactly one role |

## 3. Project objectives

1. Centralise student academic records in one relational database.
2. Provide a single authenticated entry point for all roles.
3. Enforce role-based authorization **server-side** on every protected operation.
4. Support the academic lifecycle: students, courses, semesters, enrollment,
   grades, attendance, and fees.
5. Prevent duplicate and inconsistent records through database constraints.
6. Produce management reports derived from live data.
7. Maintain an audit trail of sensitive actions.
8. Deliver a professional, responsive, accessible interface.

## 4. Intended users and stakeholders

| Stakeholder | Interest |
|---|---|
| Students | View own records; enroll in courses |
| Teachers | Enter grades and attendance for assigned courses |
| Academic staff / Registrar | Manage students, courses, offerings, enrollment |
| Finance officer | Assess fees; record payments |
| Administrator | Full control, user management, audit review |
| Academic institution | Accurate records, accountability, reporting |

## 5. Product perspective

USAMIS-Python is a standalone web application with a three-tier architecture
(presentation, application, data). It is a new Python implementation developed
independently of a separate Java project, which is reference material only.

## 6. User classes and permissions

| Permission | Admin | Academic staff | Teacher | Finance | Student |
|---|:--:|:--:|:--:|:--:|:--:|
| Manage users | ✓ | | | | |
| View audit log | ✓ | | | | |
| Manage departments / programs | ✓ | ✓ | | | |
| Manage courses / semesters | ✓ | ✓ | | | |
| Manage students | ✓ | ✓ | | | |
| Manage enrollments | ✓ | ✓ | | | |
| Enter / publish grades | ✓ | | own courses | | |
| Record attendance | ✓ | | own courses | | |
| Manage fees | ✓ | | | ✓ | |
| View reports | ✓ | ✓ | ✓ | ✓ | |
| View own grades / fees / attendance | ✓ | | | | ✓ |

Permissions are declared once in `app/security/permissions.py` and enforced by
decorators in `app/security/decorators.py`.

## 7. Functional requirements

### 7.1 Authentication and authorization (FR-AUTH)

- **FR-AUTH-1** The system shall authenticate users by username and password.
- **FR-AUTH-2** Passwords shall be stored only as salted hashes (Werkzeug).
- **FR-AUTH-3** The system shall reject logins for inactive or blocked accounts.
- **FR-AUTH-4** The system shall lock an account temporarily after a configured
  number of consecutive failed attempts (default 5 attempts / 15 minutes).
- **FR-AUTH-5** State-changing browser forms shall be CSRF-protected.
- **FR-AUTH-6** Protected endpoints shall require authentication; unauthorized
  access shall produce HTTP 401 (anonymous) or 403 (insufficient role).
- **FR-AUTH-7** Post-login redirects shall be validated to prevent open redirects.
- **FR-AUTH-8** Users shall be able to change their own password.

### 7.2 Student management (FR-STU)

- **FR-STU-1** The system shall register students with a unique student number.
- **FR-STU-2** Students shall be linked to a department and academic program.
- **FR-STU-3** The system shall support search, filter, and pagination of students.
- **FR-STU-4** A student may view only their own profile; other roles require the
  `view_students` permission.
- **FR-STU-5** Student deactivation shall be a soft status change (withdrawn),
  not a destructive delete of academic history.

### 7.3 Department and program management (FR-STR)

- **FR-STR-1** The system shall manage departments with unique codes.
- **FR-STR-2** The system shall manage academic programs linked to a department,
  with duration and total credits.
- **FR-STR-3** Program codes shall be unique within a department.
- **FR-STR-4** Referential integrity shall prevent orphaned programs.

### 7.4 Course and semester management (FR-CRS)

- **FR-CRS-1** The system shall manage courses with unique codes and credit values
  (1–12).
- **FR-CRS-2** The system shall manage semesters (academic year + term) with
  registration open/closed status.
- **FR-CRS-3** The system shall manage course offerings per semester with a teacher
  and a positive capacity.
- **FR-CRS-4** A course may be offered at most once per semester.
- **FR-CRS-5** Prerequisites shall be configurable per course with an optional
  minimum grade.

### 7.5 Enrollment management (FR-ENR)

- **FR-ENR-1** Students shall submit enrollment requests for available offerings.
- **FR-ENR-2** The system shall validate eligibility server-side before accepting
  a request (Algorithm 1).
- **FR-ENR-3** Duplicate active enrollment in the same offering shall be prevented.
- **FR-ENR-4** Capacity limits shall be enforced; concurrent requests shall not
  exceed capacity (row-level locking).
- **FR-ENR-5** Academic staff shall approve or reject pending requests.
- **FR-ENR-6** Enrollment status shall be tracked (pending, enrolled, rejected,
  dropped, completed) and history retained.

### 7.6 Grade management (FR-GRD)

- **FR-GRD-1** Only the assigned teacher (or academic staff/admin) shall enter
  grades for a course.
- **FR-GRD-2** Grades shall be numeric in the range 0–100 with a letter mapping.
- **FR-GRD-3** Publication shall be explicit; unpublished grades shall be hidden
  from students and excluded from averages.
- **FR-GRD-4** Grade creation, change, and publication shall be audited.

### 7.7 Attendance management (FR-ATT)

- **FR-ATT-1** Teachers shall record attendance for their offerings.
- **FR-ATT-2** Status shall be one of present, absent, late, excused.
- **FR-ATT-3** Duplicate records for the same student, offering, and date shall be
  prevented.
- **FR-ATT-4** Students shall view only their own attendance.

### 7.8 Fee management (FR-FEE)

- **FR-FEE-1** The system shall manage fee categories with default amounts.
- **FR-FEE-2** Assessments shall be recorded per student, category, and semester.
- **FR-FEE-3** Payments shall be recorded with a positive amount and an optional
  unique reference.
- **FR-FEE-4** Balances shall be computed with decimal-safe arithmetic (Algorithm 3).
- **FR-FEE-5** Overpayments shall be reported as a credit, never a negative balance.
- **FR-FEE-6** Students shall view only their own fee account.

### 7.9 Dashboards and reports (FR-RPT)

- **FR-RPT-1** Each role shall have a dashboard built from live database data.
- **FR-RPT-2** The system shall provide reports: students per department,
  enrollment by status, grade distribution, fee defaulters, low attendance.
- **FR-RPT-3** No fabricated or hardcoded statistics shall be displayed.

### 7.10 Audit logging (FR-AUD)

- **FR-AUD-1** Sensitive actions shall be logged with actor, action, entity,
  timestamp, and a safe summary.
- **FR-AUD-2** Audit logs shall never contain passwords or secrets.
- **FR-AUD-3** Audit-log access shall be restricted to administrators.

## 8. Non-functional requirements

- **NFR-1 (Security)** Parameterized ORM queries only; no string-concatenated SQL.
- **NFR-2 (Security)** Security headers: `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, `Permissions-Policy`.
- **NFR-3 (Security)** `debug=True` shall never be enabled in production.
- **NFR-4 (Reliability)** Multi-step writes shall use transactions.
- **NFR-5 (Maintainability)** Business logic shall live in services; routes stay thin.
- **NFR-6 (Testability)** Algorithms shall be pure and independently testable.
- **NFR-7 (Usability)** The interface shall be responsive and accessible.
- **NFR-8 (Portability)** Configuration shall be via environment variables.
- **NFR-9 (Performance)** List views shall paginate (default 15 rows).

## 9. External interface requirements

- **Web UI**: HTML5, CSS3, vanilla JavaScript over HTTPS.
- **Database**: PostgreSQL via psycopg2/SQLAlchemy.
- **CLI**: `flask db …`, `flask seed`, `flask create-admin`, `flask db-status`.

## 10. Database and data requirements

Sixteen core entities are described in `docs/DATABASE_DESIGN.md`; money uses
`NUMERIC(12,2)`, grades `NUMERIC(5,2)`, and timestamps are timezone-aware UTC.

## 11. Business rules

- **BR-1** A student may not hold two active enrollments in one offering.
- **BR-2** Enrollment requires an active student and an open, active offering.
- **BR-3** Enrollment may not exceed offering capacity.
- **BR-4** Prerequisites require a published passing grade.
- **BR-5** Grades are 0–100; unpublished grades never affect averages.
- **BR-6** Outstanding balance = total assessments − adjustments − valid payments.
- **BR-7** Payment amounts must be positive; references are unique.

## 12. Security requirements

Covered by NFR-1…NFR-3 and FR-AUTH-1…8, verified by the security test suite
(`tests/security/`).

## 13. Use cases (summary)

| ID | Use case | Primary actor |
|---|---|---|
| UC-1 | Sign in / sign out | All |
| UC-2 | Manage student records | Academic staff, Admin |
| UC-3 | Manage courses / semesters / offerings | Academic staff, Admin |
| UC-4 | Request enrollment | Student |
| UC-5 | Approve / reject enrollment | Academic staff, Admin |
| UC-6 | Enter and publish grades | Teacher |
| UC-7 | Record attendance | Teacher |
| UC-8 | Assess fees and record payments | Finance |
| UC-9 | View reports | Admin, Staff, Finance |
| UC-10 | View audit log | Admin |

**UC-4 alternative flow**: if eligibility fails, the system returns a structured
reason (duplicate, capacity full, prerequisite unmet, registration closed, inactive
student) and no enrollment is created.

## 14. Constraints and assumptions

- The application targets CPython 3.11+ and PostgreSQL 12+.
- The development server is not a production server.
- Fee recording is not a payment gateway.

## 15. Acceptance criteria

1. The application starts and serves all listed pages.
2. Migrations create the full schema on a fresh database.
3. The test suite passes (see testing report for actual results).
4. RBAC is enforced server-side for every protected route.
5. All five diagrams and required documents exist.

## 16. Traceability (requirements → tests)

| Requirement | Test file |
|---|---|
| FR-AUTH-1…8 | `tests/integration/test_auth_workflow.py`, `tests/security/test_security_controls.py` |
| FR-AUTH-6 (RBAC) | `tests/security/test_access_control.py`, `tests/unit/test_permissions.py` |
| FR-STU-4 (ownership) | `tests/security/test_access_control.py` |
| FR-ENR-2,4, BR-1…4 | `tests/integration/test_enrollment_algorithm.py`, `tests/integration/test_prerequisites.py` |
| FR-GRD-1…4, BR-5 | `tests/integration/test_persistence.py`, `tests/unit/test_academic_performance.py` |
| FR-FEE-3…5, BR-6,7 | `tests/integration/test_fee_workflow.py`, `tests/unit/test_fee_balance.py` |
| FR-AUD-1…3 | `tests/integration/test_persistence.py`, `tests/integration/test_auth_workflow.py` |
| NFR-1,2 | `tests/security/test_security_controls.py` |
