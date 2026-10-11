# Database Design — USAMIS-Python

PostgreSQL 17, SQLAlchemy 2.0 declarative models, Flask-Migrate/Alembic
versioned migrations.

## 1. Entity list

| # | Entity | Table | Purpose |
|---|---|---|---|
| 1 | User | `users` | authenticated account with one role |
| 2 | Student | `students` | student profile and academic standing |
| 3 | Teacher | `teachers` | teaching staff profile |
| 4 | Department | `departments` | academic department |
| 5 | AcademicProgram | `academic_programs` | programme within a department |
| 6 | Course | `courses` | course catalogue entry |
| 7 | Prerequisite | `prerequisites` | course → required course edge |
| 8 | Semester | `semesters` | academic year + term |
| 9 | CourseOffering | `course_offerings` | a course taught in a semester |
| 10 | Enrollment | `enrollments` | student ↔ offering registration |
| 11 | Grade | `grades` | score for an enrollment |
| 12 | Attendance | `attendance` | per-session attendance |
| 13 | FeeCategory | `fee_categories` | type of fee |
| 14 | FeeAssessment | `fee_assessments` | amount billed to a student |
| 15 | Payment | `payments` | recorded payment |
| 16 | AuditLog | `audit_logs` | immutable action record |

`roles`/`permissions` are modelled in code (`app/security/permissions.py`)
rather than as tables: roles are a fixed, small enumeration and the matrix is
the security source of truth. This keeps authorization data out of the
mutable database.

## 2. Primary and foreign keys

Every table has an integer surrogate primary key `id`. Foreign keys:

| Table | Foreign keys | On delete |
|---|---|---|
| `students` | user_id→users, department_id→departments, program_id→academic_programs | SET NULL |
| `teachers` | user_id→users, department_id→departments | SET NULL |
| `academic_programs` | department_id→departments | RESTRICT |
| `courses` | department_id→departments | SET NULL |
| `prerequisites` | course_id→courses, required_course_id→courses | CASCADE |
| `course_offerings` | course_id→courses, semester_id→semesters, teacher_id→teachers | RESTRICT / SET NULL |
| `enrollments` | student_id→students, offering_id→course_offerings, decided_by_id→users | RESTRICT / SET NULL |
| `grades` | enrollment_id→enrollments, student_id→students, entered_by_id→users | CASCADE / RESTRICT / SET NULL |
| `attendance` | student_id→students, offering_id→course_offerings, recorded_by_id→users | RESTRICT / SET NULL |
| `fee_assessments` | student_id→students, category_id→fee_categories, semester_id→semesters, created_by_id→users | RESTRICT / SET NULL |
| `payments` | student_id→students, assessment_id→fee_assessments, recorded_by_id→users | RESTRICT / SET NULL |
| `audit_logs` | actor_id→users | SET NULL |

Academic history is never cascade-deleted from a user or student; deletion of
`users` sets references to NULL rather than destroying records.

## 3. Constraints and unique keys

| Constraint | Table | Definition |
|---|---|---|
| `uq_course_code` | courses | unique `code` |
| `ck_course_credits_range` | courses | `credits` between 1 and 12 |
| `uq_prereq_pair` | prerequisites | unique (course_id, required_course_id) |
| `ck_prereq_not_self` | prerequisites | course_id ≠ required_course_id |
| `uq_semester_year_term` | semesters | unique (academic_year, term) |
| `ck_semester_term_valid` | semesters | term in fall/spring/summer |
| `uq_offering_course_semester` | course_offerings | unique (course_id, semester_id) |
| `ck_offering_capacity_positive` | course_offerings | capacity > 0 |
| `uq_enrollment_student_offering_status` | enrollments | unique (student_id, offering_id, status) |
| `ck_enrollment_status_valid` | enrollments | status in a fixed set |
| `uq_grade_enrollment` | grades | one grade per enrollment |
| `ck_grade_score_range` | grades | score null or 0–100 |
| `uq_attendance_student_offering_date` | attendance | unique (student_id, offering_id, session_date) |
| `ck_attendance_status_valid` | attendance | status in present/absent/late/excused |
| `uq_payment_reference` | payments | unique reference |
| `ck_payment_amount_positive` | payments | amount > 0 |
| `ck_fee_amount_non_negative` | fee_assessments | amount ≥ 0 |
| `ck_fee_adjustment_non_negative` | fee_assessments | adjustment ≥ 0 |
| `uq_fee_assessment_student_category_semester` | fee_assessments | unique triple |

## 4. Indexes

Indexed columns include: `users.username`, `users.email`, `students.student_number`,
`students.department_id`, `students.program_id`, `courses.code`,
`course_offerings.course_id/semester_id/teacher_id`, `enrollments.student_id/offering_id`,
`grades.student_id`, `attendance.student_id/offering_id/session_date`,
`fee_assessments.student_id/category_id/semester_id`, `payments.student_id`,
`audit_logs.actor_id/action/created_at`, and a composite
`ix_audit_logs_entity` on (entity_type, entity_id).

## 5. Numeric types

- Money: `NUMERIC(12, 2)`.
- Grades: `NUMERIC(5, 2)`.
- Prerequisite minimum grade: `NUMERIC(5, 2)`.

## 6. Business-rule enforcement in the schema

- Duplicate active enrollment — unique constraint plus an application check.
- Duplicate attendance — unique constraint.
- Invalid money — check constraints (non-negative amount, positive payment).
- Invalid grades — check constraint (0–100).
- Orphaned references — foreign keys with `RESTRICT` on academic history.

## 7. Grade publication model

`grades.is_published` (bool) and `grades.published_at` (timestamptz) model
publication explicitly. Queries for student views and performance calculations
filter on `is_published` being true.

## 8. Timestamps

All timestamps are `timestamptz` and written in UTC (`utcnow()`), then
displayed consistently in the UI.

## 9. Migrations

```
flask --app wsgi db migrate -m "message"   # generate a revision (needs app context)
flask --app wsgi db upgrade                # apply
flask --app wsgi db downgrade              # roll back one revision
flask --app wsgi db current                # show current revision
```

The initial revision creates all sixteen tables; a fresh `usamis_dev` database
was upgraded successfully (verified — 17 tables including `alembic_version`).

Never reset a populated database without explicit approval. Never delete
migration history.
