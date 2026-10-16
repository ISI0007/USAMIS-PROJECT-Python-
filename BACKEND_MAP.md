# USAMIS — Backend Code Map

**Project:** USAMIS-PROJECT-Python · Academic Management Information System
**Stack:** Python 3.11 · Flask (blueprints) · SQLAlchemy ORM · PostgreSQL · WTForms · Jinja2
**Pattern:** Application factory + Blueprint modules + a Service layer + pure Algorithm modules

This document names **every backend file** and what lives inside it, so the codebase can
be walked through quickly. Line counts are approximate.

---

## 1. Application entry points

| File | Lines | What it contains |
|---|---|---|
| `run.py` | 20 | Development runner — starts the Flask dev server. |
| `wsgi.py` | 12 | **WSGI entry point** used by production servers (gunicorn/waitress). |
| `serve.py` | 31 | Stable demo/dev server entry point (`main()`). |

---

## 2. Core application wiring

| File | Lines | What it contains |
|---|---|---|
| `app/__init__.py` | 194 | **Application factory.** `create_app()`, `_init_extensions()`, `_register_blueprints()`, `_register_error_handlers()`, `_register_security_headers()`, `_register_cli()`, and `_ensure_schema()` (idempotent additive schema guard). |
| `app/config.py` | 95 | `BaseConfig`, `DevelopmentConfig`, `TestingConfig`, `ProductionConfig`, `get_config()`. |
| `app/extensions.py` | 20 | Flask extension singletons (`db`, `migrate`, `login_manager`, `csrf`, `limiter`). |
| `app/cli.py` | 82 | Custom Flask CLI commands: `seed_command`, `seed_java_command`, `create_admin_command`, `db_status_command`. |

---

## 3. Data models (database tables) — `app/models/`

| File | Lines | Tables / classes inside |
|---|---|---|
| `__init__.py` | 49 | Re-exports every model for convenient import. |
| `academic.py` | 255 | `Department`, `AcademicProgram`, `Student`, `Teacher`, `Course`, `Prerequisite`, `Semester`, `CourseOffering` — the academic core. |
| `user.py` | 113 | `User` (authenticated account, one role), `AuditLog` (immutable action record). |
| `enrollment.py` | 73 | `Enrollment` — a student registered in a course offering. |
| `grade.py` | 57 | `Grade` — numeric 0–100 grade for one enrollment, with publication state. |
| `attendance.py` | 62 | `Attendance` — one record per (student, offering, date). |
| `attendance_session.py` | 55 | `AttendanceSession` — a QR attendance session for an offering on a date. |
| `fee.py` | 120 | `FeeCategory`, `FeeAssessment`, `Payment`. |
| `payment_intent.py` | 67 | `PaymentIntent` — one online payment attempt. |
| `notification.py` | 48 | `SmsMessage` — one outbound SMS. |
| `parent_link.py` | 57 | `ParentLink` — links a parent account to a student. |
| `mixins.py` | 21 | `TimestampMixin` (created/updated UTC), `utcnow()`. |

---

## 4. Blueprints (routes / controllers)

Each `__init__.py` below is the **controller** (URL routes + view functions); `forms.py` holds its WTForms.

| Blueprint | Lines | Routes / views inside |
|---|---|---|
| `app/auth/` | 233 + 63 | `login`, `register`, `logout`, `profile`, `upload_photo`, `remove_photo`, `change_password`. Forms: `LoginForm`, `RegistrationForm`, `ProfileForm`, `PasswordChangeForm`. |
| `app/dashboard/` | 297 | Role-specific dashboards: `home`, `_admin_dashboard`, `_staff_dashboard`, `_teacher_dashboard`, `_finance_dashboard`, `_parent_dashboard`, `_student_dashboard` + chart helpers. |
| `app/students/` | 154 + 26 | `index`, `profile`, `create`, `edit`, `deactivate`. |
| `app/courses/` | 197 + 21 | `index`, `detail`, `create`, `edit`, `add_prerequisite` + `_maybe_create_offering`, `_teacher_id_for`. |
| `app/departments/` | 79 + 12 | `index`, `create`, `edit`. |
| `app/programs/` | 90 + 18 | `index`, `create`, `edit`. |
| `app/semesters/` | 162 + 23 | `index`, `create`, `edit`, `offerings`, `create_offering`, `edit_offering`. |
| `app/enrollments/` | 131 + 10 | `index`, `decide`, `drop`, `my_enrollments`, `request_enrollment`, `check`. |
| `app/grades/` | 278 + 13 | `index`, `manage`, `enter`, `update_record`, `entry`, `save`, `my_grades` + `_gpa_bands`, `_course_pass_rate`. |
| `app/attendance/` | 217 + 14 | `index`, `record`, `my_attendance`, `qr_session`, `qr_close`, `qr_scan`, `qr_image`. |
| `app/fees/` | 167 + 42 | `index`, `create_category`, `assess`, `pay`, `student_fees`, `my_fees`. |
| `app/payments/` | 128 | `index`, `my_payments`, `start`, `checkout`, `callback`. |
| `app/notifications/` | 148 | `sms_index`, `sms_compose`, `sms_fee_reminders`. |
| `app/reports/` | 520 | Management reports + analytics: `index`, `render_fragment`, `index_pdf`, `index_docx`, `fee_defaulters(+_pdf/_docx)`, `low_attendance(+_pdf/_docx)`, `analytics_view/_pdf/_docx`, `_report_registry` + document builders. |
| `app/predictions/` | 67 | `index` (cohort risk board), `student_detail` (explainable prediction). |
| `app/records/` | 93 | `my_records`, `student_records` — per-student academic record view. |
| `app/parents/` | 102 | `index`, `student_detail` — the parent portal. |
| `app/admin/` | 146 + 16 | `index`, `users`, `create_user`, `edit_user`, `toggle_user`, `roles`, `audit_log`. |

---

## 5. Security

| File | Lines | What it contains |
|---|---|---|
| `app/security/__init__.py` | 16 | Package exports for permissions + decorators. |
| `app/security/permissions.py` | 155 | `Role`, `Permission` enums, `permissions_for()`, `role_has_permission()` — the RBAC matrix. |
| `app/security/decorators.py` | 82 | `login_required`, `permission_required`, `roles_required`, `admin_required`, `is_safe_redirect`. |

---

## 6. Service layer (business rules) — `app/services/`

| File | Lines | What it contains |
|---|---|---|
| `__init__.py` | 9 | Service-layer package doc. |
| `grade_service.py` | 111 | `GradeError`, `teacher_teaches()`, `record_grade()`, `publish_grade()`. |
| `grade_scale.py` | 74 | `letter_for_score()`, `points_for_score()`, `points_for_letter()`, `is_pass()`, `scale_as_json()` — the +/− GPA scale. |
| `enrollment_service.py` | 149 | `evaluate()`, `request_enrollment()`, `decide()`, `drop_enrollment()` (+ row locking). |
| `fee_service.py` | 124 | `FeeError`, `student_balance()`, `assess_fee()`, `record_payment()`. |
| `payment_gateway_service.py` | 123 | `start_intent()`, `confirm_intent()`, `fail_intent()` — online payments. |
| `notification_service.py` | 103 | `SmsError`, `send_sms()`, `compose_fee_reminder()`, `send_fee_reminder()`, receipts. |
| `qr_attendance_service.py` | 152 | `generate_token()`, `verify_token()`, `open_session()`, `close_session()`, `scan()`. |
| `prediction_service.py` | 82 | `student_signals()`, `predict_for_student()`, `predict_cohort()`. |
| `academic_records_service.py` | 271 | `RecordRow`, `RecordsPage`, `get_records()` (filtered/paginated), `summary_for()`. |
| `parent_service.py` | 45 | `linked_students()`, `link_for()`, `relationship_label()`. |
| `report_documents.py` | 253 | `ReportDoc`, `build_pdf()`, `build_docx()` — shared letterhead document builder. |
| `analytics_documents.py` | 312 | The five analytics builders: `revenue_summary_doc`, `course_pass_rate_doc`, `at_risk_doc`, `gpa_transcripts_doc`, `enrollment_summary_doc`. |
| `avatars.py` | 75 | `AvatarError`, `save_avatar()`, `remove_avatar()` — profile-photo handling. |
| `audit.py` | 61 | `log_action()` — writes audit entries. |

---

## 7. Algorithms (pure, deterministic, explainable) — `app/algorithms/`

| File | Lines | What it contains |
|---|---|---|
| `__init__.py` | 39 | Package doc for the explainable algorithms. |
| `enrollment_eligibility.py` | 211 | **Algorithm 1** — `EligibilityResult`, `check_capacity()`, `evaluate_enrollment()`, prerequisite checks. |
| `academic_performance.py` | 169 | **Algorithm 2** — `GradeLine`, `PerformanceResult`, `letter_for()`, `grade_point_for()`, `calculate_performance()` (credit-weighted). |
| `fee_balance.py` | 128 | **Algorithm 3** — `FeeResult`, `calculate_fee_balance()`. |
| `performance_prediction.py` | 154 | **Algorithm 4** — `Factor`, `PredictionResult`, `predict_performance()`, `band_label()`, `recommended_action()` (explainable AI risk band). |

---

## 8. Integrations (external providers, behind adapters)

| File | Lines | What it contains |
|---|---|---|
| `app/integrations/__init__.py` | 124 | `SmsProvider` / `StubSmsProvider`, `PaymentProvider` / `StubPaymentProvider`, `get_sms_provider()`, `get_payment_provider()` — stub by default, no real network calls. |

---

## 9. Seed & data import

| File | Lines | What it contains |
|---|---|---|
| `app/seed.py` | 465 | Synthetic demo data: `_get_or_create()`, `_reset()`, `run_seed()` + the 8-semester Software Engineering `CURRICULUM` and `PREREQUISITES`. |
| `app/java_seed_bridge.py` | 370 | `reconcile_java_seed()` — merges the Java reference roster into the Python DB; `_distribute_across_departments()`. |
| `app/jit_data.py` | 53 | Real JIT departments/schools (from jit.edu.cn) and their majors. |
| `app/jit_seed.py` | 35 | `seed_jit_departments()` — applies the JIT departments + majors. |

---

## 10. Database migrations — `migrations/`

| File | Lines | What it contains |
|---|---|---|
| `env.py` | 56 | Flask-Migrate/Alembic environment config. |
| `versions/a5dbe550ba23_initial_schema.py` | 362 | Initial schema. |
| `versions/b7c1a5f0d9e2_active_enrollment_unique_index.py` | 69 | Partial unique index: one active enrollment per (student, offering). |
| `versions/0f6f7e1bddda_payment_intents.py` | 66 | Payment intents table. |
| `versions/13a1f5be845f_attendance_sessions_and_qr_source.py` | 64 | Attendance sessions + QR source. |
| `versions/54e0a006ac18_sms_messages.py` | 55 | SMS messages table. |
| `versions/c9f2b7e4a1d3_parent_links.py` | 45 | Parent links table. |

---

## 11. Supporting scripts — `scripts/`

| File | Lines | What it contains |
|---|---|---|
| `smoke.py` | 77 | Boots the app, logs in as each role, hits key pages. |
| `verify_features.py` | 110 | End-to-end feature verification across all roles. |
| `verify_pages.py` | 75 | Crawls every GET page per role; reports non-2xx/3xx and 500s. |
| `verify_ui.py` | 117 | Deep per-role UI verification (nav links etc.). |
| `verify_pptx.py` | 35 | Verifies the generated PPTX opens and is readable. |
| `capture_screenshots.py` | 101 | Captures real screenshots of the running app. |
| `make_pptx.py` | 299 | Generates the USAMIS-Python PowerPoint presentation. |
| `_csrf_check.py`, `_csrf_repro.py`, `_repro_csrf_bug.py` | 30 / 62 / 34 | CSRF login/regression diagnostics. |
| `_diag_login.py`, `_inspect_login.py` | 39 / 24 | Login diagnostics. |
| `_live_smoke.py`, `_shoot_new.py`, `_verify_pages.py` | 60 / 59 / 45 | Live smoke, screenshot capture, page verification. |

---

## 12. Tests

| Path | What it covers |
|---|---|
| `tests/` | Pytest suite (166 tests) — unit + integration across auth, grades, fees, enrollment, permissions, reports. |

---

## Quick orientation

- **Startup flow:** `run.py` / `wsgi.py` → `app/__init__.py::create_app()` → registers blueprints → binds models to PostgreSQL.
- **Request flow:** Blueprint view → *Service* (`app/services/`) → *Algorithm* (`app/algorithms/`) → Model (`app/models/`) → DB.
- **Security:** every protected view is wrapped with `permission_required(...)`; the RBAC matrix lives in `app/security/permissions.py`.
- **Route count:** 91 application routes (plus static).

> Frontend files (Jinja templates in `app/templates/`, CSS in `app/static/css/app.css`, JS in `app/static/js/app.js`) are intentionally **not** listed here — this map covers the backend only.
