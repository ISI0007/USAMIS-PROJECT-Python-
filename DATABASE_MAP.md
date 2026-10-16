# USAMIS — Database & Data Flow (PostgreSQL)

This document answers three questions for the database walkthrough:

1. **Where is the database defined?** (there is no hand-written `.sql` file — see §1)
2. **How does data get IN?** (§3 — the write path, per file)
3. **How is data shown while it runs?** (§4 — the read path, per file)

It also ships with **`schema.sql`** — real PostgreSQL `CREATE TABLE` DDL generated
from the live database, so the schema can be read like a classic DB-system file.

---

## 1. Where the database lives in the code

| Concern | File | Why it matters |
|---|---|---|
| **Table definitions (true source)** | `app/models/*.py` | One Python class per table — columns, types, keys, relationships |
| Models export | `app/models/__init__.py` | Makes every model importable |
| Shared timestamp columns | `app/models/mixins.py` | `created_at` / `updated_at` |
| DB connection string | `.env` → `DATABASE_URL` | `postgresql+psycopg2://…@localhost:5432/usamis_dev` |
| Connection template | `.env.example` | Safe example, no secrets |
| Config classes | `app/config.py` | Reads `DATABASE_URL`, engine options |
| Extension singleton | `app/extensions.py` | `db = SQLAlchemy()` — the ORM handle |
| **Schema changes over time** | `migrations/versions/*.py` | 6 Alembic revisions (history of the schema) |
| Migration config | `migrations/alembic.ini`, `migrations/env.py` | How `flask db upgrade` works |
| **Generated DDL file** | `schema.sql` | The schema written as real SQL (readable like a DB course file) |
| Seed / demo rows | `app/seed.py`, `app/jit_seed.py`, `app/java_seed_bridge.py` | Inserts the demo data |
| CLI to build & fill the DB | `app/cli.py` | `flask db upgrade`, `flask seed` |

> **Note for the report:** this is a *code-first* database design — the schema is defined
> in Python (SQLAlchemy models), and `schema.sql` is generated from it. This is the modern
> equivalent of a `.sql` schema file and is provided here so the DB structure can be read
> as plain SQL.

---

## 2. How the ORM connects (the bridge)

```
.env  ──(DATABASE_URL)──►  app/config.py  ──►  Flask config
                                     │
                          app/extensions.py  (db = SQLAlchemy())
                                     │
                          app/__init__.py::create_app()
                                     │  db.init_app(app)
                                     ▼
                 SQLAlchemy ORM  ──►  psycopg2  ──►  PostgreSQL (usamis_dev)
                                     ▲
                          app/models/*.py  (the tables)
```

Every read/write in the app goes through `db.session` (SQLAlchemy), never raw SQL.

---

## 3. How data gets IN (the write path)

Each row below shows: **who enters it → the file that handles it → the service → the model → the table.**

### 3.1 Students
| Step | File |
|---|---|
| Form UI | `app/templates/students/form.html` |
| Form fields | `app/students/forms.py` → `StudentForm` |
| Route / view | `app/students/__init__.py` → `create()`, `edit()` |
| Model / table | `app/models/academic.py` → `Student` → **`students`** |

### 3.2 Courses
| Step | File |
|---|---|
| Form UI | `app/templates/courses/form.html` |
| Form fields | `app/courses/forms.py` → `CourseForm` |
| Route / view | `app/courses/__init__.py` → `create()`, `edit()` |
| Model / table | `app/models/academic.py` → `Course` → **`courses`** |

### 3.3 Enrollments (with eligibility check)
| Step | File |
|---|---|
| Form UI | `app/templates/enrollments/request.html` |
| Route / view | `app/enrollments/__init__.py` → `request_enrollment()`, `decide()` |
| **Business rules** | `app/services/enrollment_service.py` → `request_enrollment()`, `decide()` |
| **Algorithm (eligibility)** | `app/algorithms/enrollment_eligibility.py` → `evaluate_enrollment()` |
| Model / table | `app/models/enrollment.py` → `Enrollment` → **`enrollments`** |

### 3.4 Grades
| Step | File |
|---|---|
| Form UI | `app/templates/grades/manage.html`, `entry.html` |
| Form fields | `app/grades/forms.py` → `GradeForm` |
| Route / view | `app/grades/__init__.py` → `enter()`, `update_record()`, `save()` |
| **Business rules** | `app/services/grade_service.py` → `record_grade()`, `publish_grade()` |
| **Grade scale** | `app/services/grade_scale.py` → `letter_for_score()`, `points_for_score()` |
| Model / table | `app/models/grade.py` → `Grade` → **`grades`** |

### 3.5 Attendance (manual + QR)
| Step | File |
|---|---|
| Form UI | `app/templates/attendance/record.html`, `qr_session.html` |
| Route / view | `app/attendance/__init__.py` → `record()`, `qr_session()`, `qr_image()` |
| **Business rules** | `app/services/qr_attendance_service.py` → `open_session()`, `scan()` |
| Model / tables | `app/models/attendance.py` → `Attendance` → **`attendance`**; `app/models/attendance_session.py` → **`attendance_sessions`** |

### 3.6 Fees & Payments
| Step | File |
|---|---|
| Form UI | `app/templates/fees/assess_form.html`, `pay_form.html`; `payments/checkout.html` |
| Form fields | `app/fees/forms.py` → `FeeCategoryForm`, `AssessmentForm`, `PaymentForm` |
| Route / view | `app/fees/__init__.py` → `assess()`, `pay()`; `app/payments/__init__.py` → `start()`, `callback()` |
| **Business rules** | `app/services/fee_service.py` → `assess_fee()`, `record_payment()`; `app/services/payment_gateway_service.py` → `start_intent()`, `confirm_intent()` |
| **Algorithm (balance)** | `app/algorithms/fee_balance.py` → `calculate_fee_balance()` |
| Model / tables | `app/models/fee.py` → `FeeCategory`/`FeeAssessment`/`Payment` → **`fee_categories`**, **`fee_assessments`**, **`payments`**; `app/models/payment_intent.py` → **`payment_intents`** |

### 3.7 SMS notifications
| Step | File |
|---|---|
| Form UI | `app/templates/notifications/sms_compose.html`, `sms_fee_reminders.html` |
| Route / view | `app/notifications/__init__.py` → `sms_compose()`, `sms_fee_reminders()` |
| **Business rules** | `app/services/notification_service.py` → `send_sms()`, `send_fee_reminder()` |
| **Provider adapter** | `app/integrations/__init__.py` → `StubSmsProvider` (no real network call) |
| Model / table | `app/models/notification.py` → `SmsMessage` → **`sms_messages`** |

### 3.8 User accounts & audit
| Step | File |
|---|---|
| Form UI | `app/templates/admin/user_form.html`, `auth/register.html` |
| Route / view | `app/admin/__init__.py`, `app/auth/__init__.py` |
| **Audit writes** | `app/services/audit.py` → `log_action()` |
| Model / tables | `app/models/user.py` → `User`, `AuditLog` → **`users`**, **`audit_logs`** |

### 3.9 Parent links & predictions
| Step | File |
|---|---|
| Route / view | `app/parents/__init__.py`, `app/predictions/__init__.py` |
| **Business rules** | `app/services/parent_service.py`, `app/services/prediction_service.py` |
| **Algorithm (AI prediction)** | `app/algorithms/performance_prediction.py` → `predict_performance()` |
| Model / table | `app/models/parent_link.py` → `ParentLink` → **`parent_links`** |

---

## 4. How data is SHOWN (the read path)

Same pattern in reverse: **route → service → model (→ algorithm) → template.**

| Page shown | Route file | Reads via | Model(s) | Table(s) | Template |
|---|---|---|---|---|---|
| Dashboard | `app/dashboard/__init__.py` | direct queries + aggregates | many | many | `templates/dashboard/*.html` |
| Course list | `app/courses/__init__.py` | query | `Course` | `courses` | `courses/index.html` |
| Grade Management | `app/grades/__init__.py` | `_gpa_bands()`, `_course_pass_rate()` | `Grade`,`Enrollment`,`Course` | `grades`,`enrollments`,`courses` | `grades/manage.html` |
| Academic Records | `app/records/__init__.py` | `academic_records_service.get_records()` | `Grade`,`Enrollment` | `grades`,`enrollments` | `records/student.html` |
| Reports (analytics) | `app/reports/__init__.py` | `analytics_documents.*_doc()` | many | many | `reports/_analytics_base.html` |
| Risk board | `app/predictions/__init__.py` | `prediction_service.predict_cohort()` | `Grade`,`Attendance` | `grades`,`attendance` | `predictions/index.html` |
| Parent portal | `app/parents/__init__.py` | `parent_service.linked_students()` | `ParentLink`,`Student` | `parent_links`,`students` | `parents/detail.html` |
| Admin / audit | `app/admin/__init__.py` | query | `User`,`AuditLog` | `users`,`audit_logs` | `admin/*.html` |

**Reports are DB-derived, never fabricated** — `app/services/report_documents.py`
(`build_pdf`, `build_docx`) turns query results into letterhead PDF/DOCX, and
`app/services/analytics_documents.py` defines the five analytics reports.

---

## 5. End-to-end example: entering a grade and seeing it

```
Teacher opens /grades/manage          →  app/grades/__init__.py::manage()
  └─ template grades/manage.html renders the modal
Teacher clicks "Enter Grade"          →  JS opens modal, posts to /grades/manage/enter
  └─ app/grades/__init__.py::enter()
       └─ app/services/grade_service.py::record_grade()
            ├─ app/services/grade_scale.py::letter_for_score()   (score → letter)
            └─ db.session.add(Grade(...))                        (ORM write)
                 └─ INSERT INTO grades (...)                     (PostgreSQL)
Student opens /grades/my              →  app/grades/__init__.py::my_grades()
  └─ SELECT … FROM grades WHERE student_id = ?
       └─ template grades/my.html shows the score + letter
```

---

## 6. Running the database (commands)

```bash
# Configure the connection
copy .env.example .env      # edit DATABASE_URL

# Create the schema from migrations
flask db upgrade

# Load demo data
flask seed

# Inspect directly (psql)
psql -h localhost -U postgres -d usamis_dev -c "\dt"
psql -h localhost -U postgres -d usamis_dev -c "\d students"

# Or replay the generated DDL from scratch
psql -h localhost -U postgres -d usamis_dev -f schema.sql
```

---

## 7. Schema file included

**`schema.sql`** — 21 `CREATE TABLE` statements, 40 foreign keys, PostgreSQL dialect.
Validated by executing it against PostgreSQL in a scratch schema (then rolled back).
Generated from the live database via SQLAlchemy metadata, so it always matches runtime.
