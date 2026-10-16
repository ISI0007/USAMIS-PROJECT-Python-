-- ==========================================================================
-- USAMIS — PostgreSQL schema (generated DDL)
-- Database: usamis_dev  |  Engine: PostgreSQL
-- This file mirrors the schema actually used at runtime.
-- Source of truth in code: app/models/*.py (SQLAlchemy) + migrations/versions/*
-- ==========================================================================

BEGIN;

-- --- alembic_version -------------------------------------------
-- Alembic migration bookkeeping table (managed by `flask db migrate/upgrade`).
CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- --- departments -------------------------------------------
CREATE TABLE departments (
	id SERIAL NOT NULL, 
	code VARCHAR(16) NOT NULL, 
	name VARCHAR(160) NOT NULL, 
	description TEXT, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

-- --- fee_categories -------------------------------------------
CREATE TABLE fee_categories (
	id SERIAL NOT NULL, 
	code VARCHAR(24) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	description TEXT, 
	default_amount NUMERIC(12, 2) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

-- --- semesters -------------------------------------------
CREATE TABLE semesters (
	id SERIAL NOT NULL, 
	academic_year VARCHAR(16) NOT NULL, 
	term VARCHAR(16) NOT NULL, 
	start_date DATE, 
	end_date DATE, 
	is_active BOOLEAN NOT NULL, 
	registration_open BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_semester_year_term UNIQUE (academic_year, term), 
	CONSTRAINT ck_semester_term_valid CHECK (term IN ('fall','spring','summer'))
);

-- --- users -------------------------------------------
CREATE TABLE users (
	id SERIAL NOT NULL, 
	username VARCHAR(64) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	full_name VARCHAR(160) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role VARCHAR(32) NOT NULL, 
	is_active_flag BOOLEAN NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	last_login_at TIMESTAMP WITH TIME ZONE, 
	failed_login_count INTEGER NOT NULL, 
	locked_until TIMESTAMP WITH TIME ZONE, 
	avatar_path VARCHAR(255), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

-- --- academic_programs -------------------------------------------
CREATE TABLE academic_programs (
	id SERIAL NOT NULL, 
	code VARCHAR(16) NOT NULL, 
	name VARCHAR(160) NOT NULL, 
	department_id INTEGER NOT NULL, 
	duration_years INTEGER NOT NULL, 
	total_credits_required INTEGER NOT NULL, 
	description TEXT, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_program_dept_code UNIQUE (department_id, code), 
	CONSTRAINT ck_program_duration_positive CHECK (duration_years > 0), 
	FOREIGN KEY(department_id) REFERENCES departments (id) ON DELETE RESTRICT
);

-- --- audit_logs -------------------------------------------
CREATE TABLE audit_logs (
	id SERIAL NOT NULL, 
	actor_id INTEGER, 
	actor_username VARCHAR(64) NOT NULL, 
	action VARCHAR(64) NOT NULL, 
	entity_type VARCHAR(48) NOT NULL, 
	entity_id VARCHAR(48), 
	summary TEXT NOT NULL, 
	ip_address VARCHAR(45), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE SET NULL
);

-- --- courses -------------------------------------------
CREATE TABLE courses (
	id SERIAL NOT NULL, 
	code VARCHAR(16) NOT NULL, 
	title VARCHAR(160) NOT NULL, 
	description TEXT, 
	credits INTEGER NOT NULL, 
	department_id INTEGER, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_course_credits_range CHECK (credits > 0 AND credits <= 20), 
	CONSTRAINT uq_course_code UNIQUE (code), 
	FOREIGN KEY(department_id) REFERENCES departments (id) ON DELETE SET NULL
);

-- --- teachers -------------------------------------------
CREATE TABLE teachers (
	id SERIAL NOT NULL, 
	staff_number VARCHAR(24) NOT NULL, 
	user_id INTEGER, 
	first_name VARCHAR(80) NOT NULL, 
	last_name VARCHAR(80) NOT NULL, 
	email VARCHAR(255), 
	department_id INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL, 
	FOREIGN KEY(department_id) REFERENCES departments (id) ON DELETE SET NULL
);

-- --- course_offerings -------------------------------------------
CREATE TABLE course_offerings (
	id SERIAL NOT NULL, 
	course_id INTEGER NOT NULL, 
	semester_id INTEGER NOT NULL, 
	teacher_id INTEGER, 
	capacity INTEGER NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_offering_course_semester UNIQUE (course_id, semester_id), 
	CONSTRAINT ck_offering_capacity_positive CHECK (capacity > 0), 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE RESTRICT, 
	FOREIGN KEY(semester_id) REFERENCES semesters (id) ON DELETE RESTRICT, 
	FOREIGN KEY(teacher_id) REFERENCES teachers (id) ON DELETE SET NULL
);

-- --- prerequisites -------------------------------------------
CREATE TABLE prerequisites (
	id SERIAL NOT NULL, 
	course_id INTEGER NOT NULL, 
	required_course_id INTEGER NOT NULL, 
	min_grade NUMERIC(5, 2), 
	PRIMARY KEY (id), 
	CONSTRAINT uq_prereq_pair UNIQUE (course_id, required_course_id), 
	CONSTRAINT ck_prereq_not_self CHECK (course_id <> required_course_id), 
	FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE, 
	FOREIGN KEY(required_course_id) REFERENCES courses (id) ON DELETE CASCADE
);

-- --- students -------------------------------------------
CREATE TABLE students (
	id SERIAL NOT NULL, 
	student_number VARCHAR(24) NOT NULL, 
	user_id INTEGER, 
	first_name VARCHAR(80) NOT NULL, 
	last_name VARCHAR(80) NOT NULL, 
	email VARCHAR(255), 
	phone VARCHAR(32), 
	address VARCHAR(255), 
	date_of_birth DATE, 
	department_id INTEGER, 
	program_id INTEGER, 
	admission_date DATE, 
	enrollment_status VARCHAR(16) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_student_status_valid CHECK (enrollment_status IN ('active','graduated','suspended','withdrawn')), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL, 
	FOREIGN KEY(department_id) REFERENCES departments (id) ON DELETE SET NULL, 
	FOREIGN KEY(program_id) REFERENCES academic_programs (id) ON DELETE SET NULL
);

-- --- attendance_sessions -------------------------------------------
CREATE TABLE attendance_sessions (
	id SERIAL NOT NULL, 
	offering_id INTEGER NOT NULL, 
	session_date TIMESTAMP WITH TIME ZONE NOT NULL, 
	token VARCHAR(64) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	is_open BOOLEAN NOT NULL, 
	opened_by_id INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(offering_id) REFERENCES course_offerings (id) ON DELETE CASCADE, 
	FOREIGN KEY(opened_by_id) REFERENCES users (id) ON DELETE SET NULL
);

-- --- enrollments -------------------------------------------
CREATE TABLE enrollments (
	id SERIAL NOT NULL, 
	student_id INTEGER NOT NULL, 
	offering_id INTEGER NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	requested_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	decided_at TIMESTAMP WITH TIME ZONE, 
	decided_by_id INTEGER, 
	decision_note TEXT, 
	eligibility_reason TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_enrollment_student_offering_status UNIQUE (student_id, offering_id, status), 
	CONSTRAINT ck_enrollment_status_valid CHECK (status IN ('pending','enrolled','rejected','dropped','completed')), 
	FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE RESTRICT, 
	FOREIGN KEY(offering_id) REFERENCES course_offerings (id) ON DELETE RESTRICT, 
	FOREIGN KEY(decided_by_id) REFERENCES users (id) ON DELETE SET NULL
);

-- --- fee_assessments -------------------------------------------
CREATE TABLE fee_assessments (
	id SERIAL NOT NULL, 
	student_id INTEGER NOT NULL, 
	category_id INTEGER NOT NULL, 
	semester_id INTEGER, 
	amount NUMERIC(12, 2) NOT NULL, 
	adjustment NUMERIC(12, 2) NOT NULL, 
	due_date DATE, 
	note TEXT, 
	created_by_id INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_fee_assessment_student_category_semester UNIQUE (student_id, category_id, semester_id), 
	CONSTRAINT ck_fee_amount_non_negative CHECK (amount >= 0), 
	CONSTRAINT ck_fee_adjustment_non_negative CHECK (adjustment >= 0), 
	FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE RESTRICT, 
	FOREIGN KEY(category_id) REFERENCES fee_categories (id) ON DELETE RESTRICT, 
	FOREIGN KEY(semester_id) REFERENCES semesters (id) ON DELETE SET NULL, 
	FOREIGN KEY(created_by_id) REFERENCES users (id) ON DELETE SET NULL
);

-- --- parent_links -------------------------------------------
CREATE TABLE parent_links (
	id SERIAL NOT NULL, 
	parent_user_id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	relationship_type VARCHAR(16) NOT NULL, 
	contact_phone VARCHAR(32), 
	is_active BOOLEAN DEFAULT 'true' NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_parent_link_user_student UNIQUE (parent_user_id, student_id), 
	FOREIGN KEY(parent_user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE CASCADE
);

-- --- sms_messages -------------------------------------------
CREATE TABLE sms_messages (
	id SERIAL NOT NULL, 
	recipient VARCHAR(32) NOT NULL, 
	body TEXT NOT NULL, 
	category VARCHAR(24) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	provider VARCHAR(32), 
	provider_ref VARCHAR(64), 
	error TEXT, 
	sent_at TIMESTAMP WITHOUT TIME ZONE, 
	student_id INTEGER, 
	created_by_id INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE SET NULL, 
	FOREIGN KEY(created_by_id) REFERENCES users (id) ON DELETE SET NULL
);

-- --- attendance -------------------------------------------
CREATE TABLE attendance (
	id SERIAL NOT NULL, 
	student_id INTEGER NOT NULL, 
	offering_id INTEGER NOT NULL, 
	session_date DATE NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	note TEXT, 
	source VARCHAR(8) DEFAULT 'manual' NOT NULL, 
	session_id INTEGER, 
	recorded_by_id INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_attendance_student_offering_date UNIQUE (student_id, offering_id, session_date), 
	CONSTRAINT ck_attendance_status_valid CHECK (status IN ('present','absent','excused','late')), 
	FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE RESTRICT, 
	FOREIGN KEY(offering_id) REFERENCES course_offerings (id) ON DELETE RESTRICT, 
	FOREIGN KEY(session_id) REFERENCES attendance_sessions (id) ON DELETE SET NULL, 
	FOREIGN KEY(recorded_by_id) REFERENCES users (id) ON DELETE SET NULL
);

-- --- grades -------------------------------------------
CREATE TABLE grades (
	id SERIAL NOT NULL, 
	enrollment_id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	score NUMERIC(5, 2), 
	letter VARCHAR(4), 
	is_published BOOLEAN NOT NULL, 
	published_at TIMESTAMP WITH TIME ZONE, 
	entered_by_id INTEGER, 
	remarks TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_grade_enrollment UNIQUE (enrollment_id), 
	CONSTRAINT ck_grade_score_range CHECK (score IS NULL OR (score >= 0 AND score <= 100)), 
	FOREIGN KEY(enrollment_id) REFERENCES enrollments (id) ON DELETE CASCADE, 
	FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE RESTRICT, 
	FOREIGN KEY(entered_by_id) REFERENCES users (id) ON DELETE SET NULL
);

-- --- payments -------------------------------------------
CREATE TABLE payments (
	id SERIAL NOT NULL, 
	student_id INTEGER NOT NULL, 
	assessment_id INTEGER, 
	amount NUMERIC(12, 2) NOT NULL, 
	reference VARCHAR(48), 
	paid_on DATE NOT NULL, 
	note TEXT, 
	recorded_by_id INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_payment_reference UNIQUE (reference), 
	CONSTRAINT ck_payment_amount_positive CHECK (amount > 0), 
	FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE RESTRICT, 
	FOREIGN KEY(assessment_id) REFERENCES fee_assessments (id) ON DELETE SET NULL, 
	UNIQUE (reference), 
	FOREIGN KEY(recorded_by_id) REFERENCES users (id) ON DELETE SET NULL
);

-- --- payment_intents -------------------------------------------
CREATE TABLE payment_intents (
	id SERIAL NOT NULL, 
	student_id INTEGER NOT NULL, 
	assessment_id INTEGER, 
	amount NUMERIC(12, 2) NOT NULL, 
	currency VARCHAR(8) NOT NULL, 
	reference VARCHAR(48) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	provider VARCHAR(32), 
	provider_ref VARCHAR(64), 
	checkout_url TEXT, 
	error TEXT, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	payment_id INTEGER, 
	created_by_id INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_payment_intent_reference UNIQUE (reference), 
	CONSTRAINT ck_payment_intent_amount_positive CHECK (amount > 0), 
	FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE RESTRICT, 
	FOREIGN KEY(assessment_id) REFERENCES fee_assessments (id) ON DELETE SET NULL, 
	FOREIGN KEY(payment_id) REFERENCES payments (id) ON DELETE SET NULL, 
	FOREIGN KEY(created_by_id) REFERENCES users (id) ON DELETE SET NULL
);

-- ===================== INDEXES =====================
CREATE UNIQUE INDEX ix_departments_code ON departments (code);
CREATE UNIQUE INDEX ix_fee_categories_code ON fee_categories (code);
CREATE INDEX ix_semesters_academic_year ON semesters (academic_year);
CREATE UNIQUE INDEX ix_users_username ON users (username);
CREATE UNIQUE INDEX ix_users_email ON users (email);
CREATE INDEX ix_academic_programs_code ON academic_programs (code);
CREATE INDEX ix_academic_programs_department_id ON academic_programs (department_id);
CREATE INDEX ix_audit_logs_entity ON audit_logs (entity_type, entity_id);
CREATE INDEX ix_audit_logs_actor_id ON audit_logs (actor_id);
CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at);
CREATE INDEX ix_audit_logs_action ON audit_logs (action);
CREATE INDEX ix_courses_department_id ON courses (department_id);
CREATE UNIQUE INDEX ix_courses_code ON courses (code);
CREATE INDEX ix_teachers_department_id ON teachers (department_id);
CREATE UNIQUE INDEX ix_teachers_staff_number ON teachers (staff_number);
CREATE INDEX ix_course_offerings_teacher_id ON course_offerings (teacher_id);
CREATE INDEX ix_course_offerings_semester_id ON course_offerings (semester_id);
CREATE INDEX ix_course_offerings_course_id ON course_offerings (course_id);
CREATE INDEX ix_prerequisites_required_course_id ON prerequisites (required_course_id);
CREATE INDEX ix_prerequisites_course_id ON prerequisites (course_id);
CREATE INDEX ix_students_email ON students (email);
CREATE UNIQUE INDEX ix_students_student_number ON students (student_number);
CREATE INDEX ix_students_department_id ON students (department_id);
CREATE INDEX ix_students_program_id ON students (program_id);
CREATE INDEX ix_attendance_sessions_offering_id ON attendance_sessions (offering_id);
CREATE INDEX ix_attendance_sessions_is_open ON attendance_sessions (is_open);
CREATE UNIQUE INDEX ix_attendance_sessions_token ON attendance_sessions (token);
CREATE INDEX ix_enrollments_student_id ON enrollments (student_id);
CREATE INDEX ix_enrollments_offering_id ON enrollments (offering_id);
CREATE UNIQUE INDEX uq_active_enrollment_student_offering ON enrollments (student_id, offering_id) WHERE status IN ('pending', 'enrolled', 'completed');
CREATE INDEX ix_fee_assessments_category_id ON fee_assessments (category_id);
CREATE INDEX ix_fee_assessments_student_id ON fee_assessments (student_id);
CREATE INDEX ix_fee_assessments_semester_id ON fee_assessments (semester_id);
CREATE INDEX ix_parent_links_student_id ON parent_links (student_id);
CREATE INDEX ix_parent_links_parent_user_id ON parent_links (parent_user_id);
CREATE INDEX ix_sms_messages_category ON sms_messages (category);
CREATE INDEX ix_sms_messages_status ON sms_messages (status);
CREATE INDEX ix_sms_messages_recipient ON sms_messages (recipient);
CREATE INDEX ix_sms_messages_student_id ON sms_messages (student_id);
CREATE INDEX ix_attendance_session_id ON attendance (session_id);
CREATE INDEX ix_attendance_offering_id ON attendance (offering_id);
CREATE INDEX ix_attendance_student_id ON attendance (student_id);
CREATE INDEX ix_attendance_session_date ON attendance (session_date);
CREATE INDEX ix_grades_student_id ON grades (student_id);
CREATE INDEX ix_grades_enrollment_id ON grades (enrollment_id);
CREATE INDEX ix_payments_assessment_id ON payments (assessment_id);
CREATE INDEX ix_payments_student_id ON payments (student_id);
CREATE INDEX ix_payment_intents_payment_id ON payment_intents (payment_id);
CREATE INDEX ix_payment_intents_reference ON payment_intents (reference);
CREATE INDEX ix_payment_intents_assessment_id ON payment_intents (assessment_id);
CREATE INDEX ix_payment_intents_status ON payment_intents (status);
CREATE INDEX ix_payment_intents_student_id ON payment_intents (student_id);

COMMIT;