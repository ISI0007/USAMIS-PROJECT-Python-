"""Synthetic development/demo data generation.

SAFETY:
* Development/demo use only — synthetic data, never real student records.
* Idempotent: repeated runs upsert on natural keys and do not duplicate.
* ``--reset`` clears the demo tables first (explicit, deliberate action).
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from werkzeug.security import generate_password_hash

from .extensions import db
from .models import (
    AcademicProgram,
    Attendance,
    AuditLog,
    Course,
    CourseOffering,
    Department,
    Enrollment,
    FeeAssessment,
    FeeCategory,
    Grade,
    Payment,
    Prerequisite,
    Semester,
    Student,
    Teacher,
    User,
)

DEMO_PASSWORD = "Demo_Pass1!"  # noqa: S105 - documented demo credential


def _get_or_create(model, defaults=None, **filters):
    instance = db.session.execute(db.select(model).filter_by(**filters)).scalars().first()
    if instance:
        return instance, False
    params = dict(filters)
    if defaults:
        params.update(defaults)
    instance = model(**params)
    db.session.add(instance)
    db.session.flush()
    return instance, True


def _reset() -> None:
    """Delete demo data in dependency order (development only)."""
    for model in (
        Payment, FeeAssessment, FeeCategory, Attendance, Grade, Enrollment,
        Prerequisite, CourseOffering, Semester, Course, AcademicProgram,
        Student, Teacher, Department, AuditLog, User,
    ):
        db.session.query(model).delete()
    db.session.commit()


def run_seed(reset: bool = False) -> None:
    if reset:
        _reset()

    # --- Departments ---------------------------------------------------- #
    cs, _ = _get_or_create(Department, {"name": "Computer Science", "is_active": True,
                                        "description": "Computing and software engineering."},
                           code="CS")
    bus, _ = _get_or_create(Department, {"name": "Business Administration", "is_active": True},
                            code="BUS")
    eng, _ = _get_or_create(Department, {"name": "Engineering", "is_active": True}, code="ENG")

    # --- Programs ------------------------------------------------------- #
    bscs, _ = _get_or_create(AcademicProgram, {
        "name": "BSc Computer Science", "department_id": cs.id, "duration_years": 4,
        "total_credits_required": 120, "is_active": True}, code="BSCS")
    bba, _ = _get_or_create(AcademicProgram, {
        "name": "BBA", "department_id": bus.id, "duration_years": 4,
        "total_credits_required": 120, "is_active": True}, code="BBA")

    # --- Users ---------------------------------------------------------- #
    def account(username, email, name, role):
        user, created = _get_or_create(User, {
            "email": email, "full_name": name, "role": role,
            "status": "active", "is_active_flag": True,
            "password_hash": generate_password_hash(DEMO_PASSWORD)}, username=username)
        if created:
            # password_hash was provided above; ensure it is never null.
            pass
        return user

    admin = account("admin", "admin@usamis.demo", "System Administrator", "administrator")
    registrar = account("registrar", "registrar@usamis.demo", "Registrar Office", "academic_staff")
    finance = account("finance", "finance@usamis.demo", "Finance Officer", "finance")
    teacher_user = account("t.mensah", "t.mensah@usamis.demo", "Thomas Mensah", "teacher")
    teacher_user2 = account("a.okafor", "a.okafor@usamis.demo", "Ada Okafor", "teacher")
    student_user = account("s.demo", "s.demo@usamis.demo", "Demo Student", "student")
    db.session.commit()

    # --- Teachers ------------------------------------------------------- #
    t1, _ = _get_or_create(Teacher, {
        "first_name": "Thomas", "last_name": "Mensah", "email": teacher_user.email,
        "department_id": cs.id, "user_id": teacher_user.id}, staff_number="T-1001")
    t2, _ = _get_or_create(Teacher, {
        "first_name": "Ada", "last_name": "Okafor", "email": teacher_user2.email,
        "department_id": bus.id, "user_id": teacher_user2.id}, staff_number="T-1002")

    # --- Students ------------------------------------------------------- #
    student, _ = _get_or_create(Student, {
        "first_name": "Demo", "last_name": "Student", "email": student_user.email,
        "user_id": student_user.id, "department_id": cs.id, "program_id": bscs.id,
        "admission_date": dt.date(2023, 9, 1), "enrollment_status": "active"},
        student_number="S-2023-0001")

    for i in range(2, 13):
        _get_or_create(Student, {
            "first_name": f"Student{i:02d}", "last_name": "Sample",
            "email": f"student{i:02d}@usamis.demo", "department_id": cs.id,
            "program_id": bscs.id, "admission_date": dt.date(2023, 9, 1),
            "enrollment_status": "active"}, student_number=f"S-2023-{i:04d}")

    _get_or_create(Student, {
        "first_name": "Bella", "last_name": "Business", "email": "bella@usamis.demo",
        "department_id": bus.id, "program_id": bba.id,
        "admission_date": dt.date(2022, 9, 1), "enrollment_status": "active"},
        student_number="S-2022-0001")

    # --- Courses -------------------------------------------------------- #
    courses = {}
    for code, title, credits, dept in [
        ("CS101", "Introduction to Programming", 3, cs),
        ("CS102", "Data Structures", 4, cs),
        ("CS201", "Databases", 3, cs),
        ("CS301", "Software Engineering", 3, cs),
        ("BUS101", "Principles of Management", 3, bus),
        ("ENG101", "Engineering Mathematics I", 4, eng),
    ]:
        courses[code], _ = _get_or_create(Course, {
            "title": title, "credits": credits, "department_id": dept.id,
            "is_active": True,
            "description": f"{title} — core course."}, code=code)

    # Prerequisite: CS201 requires CS102
    _get_or_create(Prerequisite, {"min_grade": Decimal("60.00")},
                   course_id=courses["CS201"].id,
                   required_course_id=courses["CS102"].id)
    db.session.commit()

    # --- Semesters ------------------------------------------------------ #
    sem1, _ = _get_or_create(Semester, {
        "term": "fall", "start_date": dt.date(2025, 9, 1),
        "end_date": dt.date(2025, 12, 20), "is_active": True,
        "registration_open": True}, academic_year="2025/2026")
    sem2, _ = _get_or_create(Semester, {
        "term": "spring", "start_date": dt.date(2026, 1, 15),
        "end_date": dt.date(2026, 5, 30), "is_active": True,
        "registration_open": True}, academic_year="2025/2026")

    # --- Offerings ------------------------------------------------------ #
    offerings = {}
    for sem, prefix in ((sem1, "A"), (sem2, "B")):
        for idx, code in enumerate(courses.keys()):
            offering, _ = _get_or_create(CourseOffering, {
                "teacher_id": (t1 if idx % 2 == 0 else t2).id,
                "capacity": 40, "is_active": True},
                course_id=courses[code].id, semester_id=sem.id)
            offerings[(sem.id, code)] = offering
    db.session.commit()

    # --- Enrollments, grades, attendance -------------------------------- #
    all_students = db.session.execute(db.select(Student)).scalars().all()
    for s in all_students:
        for code in ["CS101", "CS102", "BUS101"]:
            offering = offerings.get((sem1.id, code))
            if not offering:
                continue
            existing = db.session.execute(
                db.select(Enrollment).where(
                    Enrollment.student_id == s.id, Enrollment.offering_id == offering.id,
                    Enrollment.status == "enrolled")
            ).scalars().first()
            if existing:
                continue
            enrollment = Enrollment(student_id=s.id, offering_id=offering.id,
                                    status="enrolled")
            db.session.add(enrollment)
            db.session.flush()

            grade = db.session.execute(
                db.select(Grade).where(Grade.enrollment_id == enrollment.id)
            ).scalars().first()
            if grade is None:
                score = Decimal("72.50") if s.id % 2 == 0 else Decimal("58.00")
                db.session.add(Grade(
                    enrollment_id=enrollment.id, student_id=s.id, score=score,
                    letter="B" if score >= 70 else "E", is_published=True,
                    published_at=dt.datetime.now(dt.timezone.utc), entered_by_id=teacher_user.id))

            for day in (dt.date(2025, 9, 8), dt.date(2025, 9, 15)):
                db.session.execute(db.select(Attendance))  # touch session
                exists = db.session.execute(
                    db.select(Attendance).where(
                        Attendance.student_id == s.id,
                        Attendance.offering_id == offering.id,
                        Attendance.session_date == day)
                ).scalars().first()
                if not exists:
                    db.session.add(Attendance(
                        student_id=s.id, offering_id=offering.id, session_date=day,
                        status="present", recorded_by_id=teacher_user.id))
    db.session.commit()

    # --- Fees ----------------------------------------------------------- #
    tuition, _ = _get_or_create(FeeCategory, {
        "name": "Tuition", "default_amount": Decimal("2500.00"),
        "is_active": True}, code="TUITION")
    library, _ = _get_or_create(FeeCategory, {
        "name": "Library", "default_amount": Decimal("150.00"),
        "is_active": True}, code="LIBRARY")

    for s in all_students:
        for cat, amt in ((tuition, Decimal("2500.00")), (library, Decimal("150.00"))):
            assessment = db.session.execute(
                db.select(FeeAssessment).where(
                    FeeAssessment.student_id == s.id,
                    FeeAssessment.category_id == cat.id,
                    FeeAssessment.semester_id == sem1.id)
            ).scalars().first()
            if assessment is None:
                assessment = FeeAssessment(
                    student_id=s.id, category_id=cat.id, semester_id=sem1.id,
                    amount=amt, adjustment=Decimal("0.00"),
                    due_date=dt.date(2025, 10, 15), created_by_id=finance.id)
                db.session.add(assessment)
                db.session.flush()

        # Give the demo student a partial payment for a realistic dashboard.
        if s.student_number == "S-2023-0001":
            existing_pay = db.session.execute(
                db.select(Payment).where(Payment.student_id == s.id,
                                         Payment.reference == "PAY-DEMO-0001")
            ).scalars().first()
            if existing_pay is None:
                db.session.add(Payment(
                    student_id=s.id, amount=Decimal("1000.00"),
                    reference="PAY-DEMO-0001", paid_on=dt.date(2025, 9, 20),
                    recorded_by_id=finance.id))
    db.session.commit()

    # --- Audit seed marker ---------------------------------------------- #
    if db.session.query(AuditLog).count() == 0:
        db.session.add(AuditLog(
            actor_id=admin.id, actor_username="admin", action="seed",
            entity_type="System", entity_id=None,
            summary="Synthetic demo data generated."))
        db.session.commit()
