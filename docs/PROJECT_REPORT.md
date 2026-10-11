# Project Report — USAMIS-Python

**University Student Academic Management Information System**

---

## Abstract

USAMIS-Python is a role-based web application that centralises university
student academic administration: student records, academic structure, course
enrollment, grades, attendance, fees, and reporting. It is implemented in
Python with Flask, SQLAlchemy, and PostgreSQL, and enforces authorization on the
server for every protected operation. Three explainable, deterministic
algorithms support enrollment eligibility, academic performance, and fee
balance calculations. The system is delivered with automated tests, five
diagrams, and a full documentation package.

## 1. Introduction and problem statement

Academic departments typically rely on spreadsheets and disconnected files.
Records duplicate, fee tracking drifts, access is uncontrolled, and management
cannot obtain timely reports. A centralised Management Information System
addresses these problems by connecting people, processes, and technology so
that raw student data becomes reliable management information.

## 2. Objectives and scope

Objectives: centralise records; provide one authenticated entry point; enforce
role-based access server-side; support the academic lifecycle; prevent duplicate
and inconsistent data; produce live reports; and maintain an audit trail.

Scope: a demonstrable academic MIS. Out of scope: real payment processing,
admissions, and any AI/ML feature.

## 3. Existing-system limitations and motivation

The reference point is a Java implementation of a comparable system. That
project is maintained separately and was used only as background; the Python
implementation was built independently. The motivation is a maintainable,
testable, and explainable Python codebase with strong server-side controls.

## 4. Proposed system

A Flask application organised as an application factory with feature
blueprints, a service layer for business rules, isolated algorithm modules, and
SQLAlchemy models over PostgreSQL. Five roles — administrator, academic staff,
teacher, finance, and student — see role-specific dashboards and may perform
only their permitted actions.

## 5. Requirements and user roles

Functional and non-functional requirements are specified in `docs/SRS.md`
(FR-AUTH, FR-STU, FR-STR, FR-CRS, FR-ENR, FR-GRD, FR-ATT, FR-FEE, FR-RPT,
FR-AUD, and NFR-1…9). The permission matrix is defined in
`app/security/permissions.py` and is the single source of truth for
authorization.

## 6. System architecture

See Figure 2 (`docs/diagrams/02-system-architecture.mmd` / `.png`) and
`docs/ARCHITECTURE.md`. Layers: browser presentation; Flask application
(blueprints, security, services, algorithms); data access (SQLAlchemy,
migrations); PostgreSQL storage.

## 7. Database design

Sixteen entities are modelled with explicit keys, constraints, and indexes. See
Figure 3 and `docs/DATABASE_DESIGN.md`. Money uses `NUMERIC(12,2)`; grades use
`NUMERIC(5,2)`; timestamps are UTC.

## 8. Diagrams

- Figure 1 — System context (`01-system-context.png`)
- Figure 2 — System architecture (`02-system-architecture.png`)
- Figure 3 — Entity relationship (`03-er-diagram.png`)
- Figure 4 — Enrollment flowchart (`04-enrollment-flowchart.png`)
- Figure 5 — Data flow (`05-data-flow-diagram.png`)

All five are provided as editable Mermaid source and exported PNG images.

## 9. Implementation and technology choices

| Layer | Technology | Rationale |
|---|---|---|
| Language | Python 3.11 | readability, ecosystem |
| Framework | Flask | lightweight, blueprint modularity |
| ORM | SQLAlchemy 2.0 | typed models, parameter binding |
| Migrations | Flask-Migrate/Alembic | versioned, reversible schema |
| Auth | Flask-Login + Werkzeug | sessions and secure hashing |
| Forms/CSRF | Flask-WTF/WTForms | validation and CSRF tokens |
| Database | PostgreSQL | constraints, numeric types, row locking |
| UI | HTML5/CSS3/vanilla JS | responsive, no heavy front-end build |

The application was built in verifiable phases: foundation, authentication and
RBAC, academic modules, algorithms, front end, tests, documentation,
presentation.

## 10. The three explainable algorithms

1. **Enrollment eligibility** — checks student status, offering state,
   registration window, duplicates, prerequisites, and capacity, returning a
   structured result with reason codes. Integrated with row locking for
   concurrency safety.
2. **Academic performance** — a credit-weighted average over published grades,
   with an optional, explicitly-configured grade-point mapping; invalid or
   unpublished data is excluded and explained.
3. **Fee balance** — outstanding balance = assessments − adjustments − payments,
   computed with decimal arithmetic, with explicit overpayment handling.

Full specifications, pseudocode, complexity, and examples are in
`docs/ALGORITHMS.md`.

## 11. Testing methodology and results

Testing uses pytest over a dedicated PostgreSQL test database with unit,
integration, and security categories. The executed suite reported **87 passed,
0 failed** (see `docs/TESTING_REPORT.md`). Six defects were discovered and fixed
during testing, including a prerequisite subquery error and a duplicate
fee-assessment gap.

## 12. Screenshots

Screenshots of the running application belong in `docs/screenshots/`. They must
be captured from the actual application; fabricated images are never used.

> Note: automated screenshot capture is not included in this submission. The
> five diagrams are exported images; application screenshots should be captured
> manually or via the browser automation skill against the running app.

## 13. Limitations

- Fee recording is not a payment gateway.
- Rate-limit storage is in-memory by default.
- Parallel-thread concurrency is verified by design and unit-level capacity
  tests, not by multi-process load testing.

## 14. Future improvements

- Student/faculty mobile client.
- Email/SMS notifications (fee reminders, results).
- A real payment-gateway integration with proper authorization.
- QR-code attendance.
- Cloud deployment with horizontal scaling and a shared rate-limit backend.
- Parent/guardian portal.

Any future performance-prediction feature is explicitly **out of scope** and is
not part of this deterministic system.

## 15. Conclusion

USAMIS-Python delivers a working, tested, documented academic MIS with
server-enforced role-based access, three explainable algorithms, accurate
diagrams, and a reproducible setup. It meets the stated objectives while
preserving the separate Java project.

## 16. References

1. Flask documentation — https://flask.palletsprojects.com/
2. SQLAlchemy 2.0 documentation — https://docs.sqlalchemy.org/
3. PostgreSQL 17 documentation — https://www.postgresql.org/docs/
4. Flask-Login, Flask-WTF, Flask-Migrate project documentation.
5. IEEE Std 830 — guide to software requirements specifications (structure
   adapted for a course project).
