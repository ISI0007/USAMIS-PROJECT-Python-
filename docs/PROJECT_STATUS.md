# USAMIS-Python — Project Status

**Document owner:** Development team
**Last updated:** 2026-10-11
**Status:** COMPLETE — implemented, tested, documented, and pushed.

---

## 1. Repository inspection

| Item | Finding |
|---|---|
| Repository URL | `https://github.com/ISI0007/USAMIS-PROJECT-Python-` |
| Default branch | `main` |
| Initial commit on `main` | `ebbc84c1091fe1cb10c3564703a84116545b5e93` |
| Initial contents | `LICENSE` only — the repository was effectively empty |
| Repository size | 0 KB (empty at inspection time) |
| GitHub identity | `ISI0007` (authenticated via GitHub CLI keyring) |
| Token scopes | `gist`, `read:org`, `repo`, `workflow` |
| Repository permissions | `admin: true`, `maintain: true`, `push: true`, `triage: true`, `pull: true` |
| **Write access** | **Confirmed available** — no push blocker |

The Java reference project (`https://github.com/ISI0007/JiT-USAMIS-PROJECT`) was
located locally at `JiT-USAMIS-PROJECT/` as a **separate Git repository**. It was
**not opened for writing, modified, deleted, or migrated**. The Python project
lives in its own directory: `USAMIS-PROJECT-Python/`.

## 2. Local environment

| Tool | Version / location | Status |
|---|---|---|
| Python | 3.11.15 (64-bit) | Available |
| Python 3.13.7 | `D:\pycharm\python3.13.7-amd64` | Available (not used) |
| pip | Installed in project virtualenv | Available |
| Git | 2.55.0.windows.5 | Available |
| PostgreSQL | 17.10 (`postgresql-x64-17`, running, port 5432) | Available |
| psql client | `D:\postgresql\bin\psql.exe` | Available |
| Node.js | v24.16.0 | Available (not required) |
| GitHub CLI | `gh` 2.x, authenticated as `ISI0007` | Available |

Databases created: `usamis_dev` (development) and `usamis_test` (testing).

## 3. Architecture selected

Modular Flask **application-factory** architecture with feature blueprints, a
service layer, isolated algorithm modules, SQLAlchemy models, and Flask-Migrate
migrations. See `docs/ARCHITECTURE.md` for full detail.

```text
Browser (HTML5 / CSS3 / JS)
        │
Flask application factory
   ├─ blueprints/  auth, dashboard, students, departments, programs,
   │               courses, semesters, enrollments, grades, attendance,
   │               fees, reports, admin
   ├─ security/    permissions (RBAC matrix), decorators (server-side)
   ├─ services/    audit, enrollment, grade, fee
   ├─ algorithms/  enrollment_eligibility, academic_performance, fee_balance
   ├─ models/      User, Student, Department, AcademicProgram, Teacher,
   │               Course, Prerequisite, Semester, CourseOffering,
   │               Enrollment, Grade, Attendance, FeeCategory,
   │               FeeAssessment, Payment, AuditLog
        │
SQLAlchemy 2.0 (parameterized ORM)
        │
PostgreSQL 17
```

## 4. Verified progress

| Phase | Description | Status |
|---|---|---|
| 0 | Repository and environment inspection | Complete |
| 1 | Project foundation (factory, config, extensions, models) | Complete |
| 2 | Authentication and RBAC | Complete |
| 3 | Core academic modules | Complete |
| 4 | Three explainable algorithms | Complete |
| 5 | Frontend templates | Complete |
| 6 | Automated test suite (87 passing) | Complete |
| 7 | Documentation and five diagrams | Complete |
| 8 | PowerPoint presentation (15 slides) | Complete |
| 9 | Final verification and push | Complete |

### Verified so far (with evidence)

- `flask db migrate` + `flask db upgrade` created **17 tables** in PostgreSQL.
- `flask seed` inserted synthetic demo data (idempotent):
  6 users, 13 students, 6 courses, 6 offerings, 39 enrollments, 39 grades,
  78 attendance rows, 26 fee assessments, 1 payment.
- `scripts/smoke.py` booted the real app and confirmed the RBAC matrix:
  - anonymous → redirected from protected routes;
  - administrator → full access;
  - academic staff → academic modules allowed, fees/admin denied (403);
  - teacher → academic read allowed, enrollments/fees/admin denied (403);
  - finance → fees allowed, enrollments/admin denied (403);
  - student → dashboards allowed, all management routes denied (403).

## 5. Identified issues and resolutions

| Issue | Resolution |
|---|---|
| `flask_limiter` missing from requirements | Added `Flask-Limiter==3.8.0` |
| `utcnow` not exported from `app.models` | Re-exported from `app/models/__init__.py` |
| Alembic `env.py` used an invalid attribute | Rewrote `migrations/env.py` for Flask-Migrate 4.x |
| Missing `migrations/versions/` directory | Created |
| Seed flushed `User` before password hashing | Set `password_hash` at insert time |

## 6. Known blockers

None. GitHub write access was available and the push succeeded.

## 7. Delivery summary

- **Tests:** 87 passed, 0 failed (`pytest`, PostgreSQL test database).
- **Fresh database migration:** verified — 17 tables created on `usamis_fresh`.
- **Diagrams:** five Mermaid sources with exported PNGs (verified PNG signatures).
- **Presentation:** `docs/USAMIS_Presentation.pptx`, 15 slides, opens in python-pptx.
- **Commit:** `d5b468c` (implementation) merged with remote `ebbc84c` (LICENSE) as
  `80f99d9`.
- **Push:** confirmed `ebbc84c..80f99d9 main -> main`; remote `main` = `80f99d9`.
- **Java project:** untouched — no tracked files modified; its `_verify/` files
  are untracked and pre-date this session.

## 8. Definition of done — evaluation

### Application
- [x] PASS — Flask application starts successfully.
- [x] PASS — PostgreSQL connectivity works.
- [x] PASS — Database migrations work (fresh DB verified).
- [x] PASS — Authentication works.
- [x] PASS — Role-based access enforced on the backend.
- [x] PASS — Core academic modules persist and retrieve data.
- [x] PASS — Enrollment eligibility validated server-side.
- [x] PASS — Grade calculations follow documented rules.
- [x] PASS — Fee calculations use decimal-safe arithmetic.
- [x] PASS — Audit logging works for required actions.
- [x] PASS — The frontend connects to real backend functionality.
- [x] PASS — Errors are handled appropriately.

### Testing
- [x] PASS — Unit tests exist for all three algorithms.
- [x] PASS — Integration tests cover core workflows.
- [x] PASS — Security tests cover critical access-control rules.
- [x] PASS — The test suite was executed (87 passed).
- [x] PASS — Results and known limitations documented.

### Academic submission
- [x] PASS — SRS complete.
- [x] PASS — Project report complete.
- [x] PASS — Architecture documentation complete.
- [x] PASS — Database documentation complete.
- [x] PASS — Algorithm documentation complete.
- [x] PASS — Installation guide complete.
- [x] PASS — User manual complete.
- [x] PASS — Testing report reflects actual results.
- [x] PASS — Five diagram sources exist.
- [x] PASS — Diagram exports verified (PNG rendering supported).
- [x] PASS — PowerPoint opens successfully.
- [ ] FAIL — Screenshots of the running application are not included; capture
  them from the live app into `docs/screenshots/` (no fabricated images used).

### Repository and reproducibility
- [x] PASS — README provides a complete setup guide.
- [x] PASS — Environment example contains no real secrets.
- [x] PASS — Dependencies documented.
- [x] PASS — A fresh development database can be migrated.
- [x] PASS — Synthetic demo data can be generated safely.
- [x] PASS — Git status inspected.
- [x] PASS — The Java project remains untouched.
- [x] PASS — GitHub upload confirmed (`main` = `80f99d9`).
