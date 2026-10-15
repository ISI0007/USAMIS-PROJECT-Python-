"""Java -> Python seed reconciliation.

The reference implementation (``JiT-USAMIS-PROJECT``, Java/Servlet) ships a
seed roster of departments, programmes, students, courses, enrolments, grades
and fee records. This module brings that data into the Python project while:

* **De-duplicating** against what the Python seed already created (matching on
  natural keys: username, student number, course code, department code), and
* **Distributing** the student cohort across *all* JIT departments instead of
  leaving every student in Software Engineering.

Idempotent: safe to run repeatedly; it upserts and never duplicates.

Reference data converted from the Java seed:
* Departments: CE, SE, ISC, EE, NS, NCE, BS, ME (mapped onto the real JIT
  department codes used in :mod:`app.jit_data`).
* Students: STU2024001..STU2024008 (Wei Zhang, Mei Liu, Jun Chen,
  Yaseen Al-Rashid, Xin Wang, Hao Li, Fang Zhou, Song Zhenhua).
* Courses: CS301, CS201, SE401, AI301, CS101, NET201, BUS201.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from .extensions import db
from .models import (
    AcademicProgram, Course, CourseOffering, Department, Enrollment,
    FeeAssessment, FeeCategory, Grade, Payment, Semester, Student,
)
from .seed import _get_or_create

# --------------------------------------------------------------------------- #
# Reference data (converted from JiT-USAMIS-PROJECT/java/.../seed.sql)
# --------------------------------------------------------------------------- #
# Java department code -> (JIT department code, JIT department name,
#                          programme name, programme code)
JAVA_DEPARTMENTS = {
    "CE":  ("0801", "School of Software Engineering", "Computer Science and Technology", "0801-CTC"),
    "SE":  ("0801", "School of Software Engineering", "Software Engineering", "0801-SE"),
    "ISC": ("0808", "College of Intelligent Science and Control Engineering", "Automation", "0808-AUT"),
    "EE":  ("0810", "School of Network and Communication Engineering",
            "Communication Engineering", "0810-CE"),
    "NS":  ("0809", "School of Network Security", "Information Security", "0809-IS"),
    "NCE": ("0810", "School of Network and Communication Engineering",
            "Communication Engineering", "0810-CE"),
    "BS":  ("0806", "Business School", "Finance", "0806-FIN"),
    "ME":  ("0802", "School of Mechanical and Electrical Engineering",
            "Mechanical Design, Manufacturing and Automation", "0802-MDM"),
}

# Java students (converted). (student_no, first, last, dob, gender, dept_code,
# programme, year, nationality, java_dept)
JAVA_STUDENTS = [
    ("STU2024001", "Wei", "Zhang", "2003-05-12", "Male", "0801", "Software Engineering", 2, "Chinese"),
    ("STU2024002", "Mei", "Liu", "2004-02-20", "Female", "0809", "Information Security", 1, "Chinese"),
    ("STU2024003", "Jun", "Chen", "2002-08-15", "Male", "0806", "Finance", 3, "Chinese"),
    ("STU2024004", "Yaseen", "Al-Rashid", "2003-11-01", "Male", "0805",
     "Software Engineering (International)", 2, "International"),
    ("STU2024005", "Xin", "Wang", "2003-07-22", "Female", "0808", "Internet of Things Engineering", 2, "Chinese"),
    ("STU2024006", "Hao", "Li", "2001-03-30", "Male", "0810", "Communication Engineering", 4, "Chinese"),
    ("STU2024007", "Fang", "Zhou", "2004-09-14", "Female", "0802",
     "Mechanical Design, Manufacturing and Automation", 1, "Chinese"),
    ("STU2024008", "Song", "Zhenhua", "2003-12-05", "Male", "0812", "Civil Engineering", 2, "Chinese"),
]

# Java courses (converted). (code, title, dept_code, credits, capacity,
#                           semester_no, status)
JAVA_COURSES = [
    ("CS301", "Database Systems", "0801", 3, 50, 1, "active"),
    ("CS201", "Data Structures and Algorithms", "0801", 4, 40, 1, "active"),
    ("SE401", "Software Engineering Principles", "0801", 3, 35, 1, "active"),
    ("AI301", "Machine Learning Fundamentals", "0805", 4, 30, 1, "active"),
    ("CS101", "Introduction to Programming", "0801", 3, 50, 1, "active"),
    ("NET201", "Network Security Basics", "0809", 3, 30, 2, "active"),
    ("BUS201", "Management Information Systems", "0806", 3, 40, 1, "active"),
]


def _year_of_study(admission_year: int, on: dt.date | None = None) -> int:
    on = on or dt.date(2026, 9, 1)
    return max(1, min(on.year - admission_year + 1, 6))


def reconcile_java_seed() -> dict:
    """Merge the Java reference roster into the Python database.

    Returns a small report dict for logging.
    """
    report = {"departments_merged": 0, "departments_created": 0,
              "programs_created": 0, "students_created": 0,
              "students_redistributed": 0, "courses_created": 0,
              "offerings_created": 0, "enrollments_created": 0,
              "grades_created": 0, "fees_created": 0}

    # --- 1. De-duplicate departments ------------------------------------ #
    # The Python seed created a bare "Software Engineering" (0809) plus the JIT
    # "School of Software Engineering" (0801). The Java roster's SE department is
    # the same institution unit; fold the legacy 0809 record into 0801 and move
    # any students across so nothing is orphaned or duplicated.
    legacy = db.session.execute(
        db.select(Department).where(Department.name == "Software Engineering")).scalars().first()
    canonical = db.session.execute(
        db.select(Department).where(Department.code == "0801")).scalars().first()
    if legacy is not None and canonical is not None and legacy.id != canonical.id:
        for prog in db.session.execute(
                db.select(AcademicProgram).where(AcademicProgram.department_id == legacy.id)).scalars():
            prog.department_id = canonical.id
        for stu in db.session.execute(
                db.select(Student).where(Student.department_id == legacy.id)).scalars():
            stu.department_id = canonical.id
            report["students_redistributed"] += 1
        for course in db.session.execute(
                db.select(Course).where(Course.department_id == legacy.id)).scalars():
            course.department_id = canonical.id
        db.session.delete(legacy)
        db.session.flush()
        report["departments_merged"] += 1
    db.session.commit()

    # --- 2. Ensure every referenced department + programme exists ------- #
    from .jit_data import JIT_DEPARTMENTS
    jit_by_code = {code: (name, majors) for code, name, _desc, majors in JIT_DEPARTMENTS}
    needed_codes = {v[0] for v in JAVA_DEPARTMENTS.values()}
    needed_codes.update(s[5] for s in JAVA_STUDENTS)
    for code in sorted(needed_codes):
        name, majors = jit_by_code.get(code, (f"Department {code}", []))
        dept, created = _get_or_create(
            Department,
            {"name": name, "is_active": True, "description": name},
            code=code)
        if created:
            report["departments_created"] += 1
        db.session.commit()
        # Ensure one programme per major so students can be assigned.
        for major in majors:
            prog_code = f"{code}-{''.join(w[0] for w in major.split())[:6].upper()}"
            _p, prog_created = _get_or_create(
                AcademicProgram,
                {"name": major, "department_id": dept.id, "duration_years": 4,
                 "total_credits_required": 137, "is_active": True},
                code=prog_code)
            if prog_created:
                report["programs_created"] += 1
        db.session.commit()

    def dept_by_code(code):
        return db.session.execute(
            db.select(Department).where(Department.code == code)).scalars().first()

    def program_for(dept_code, program_name):
        dept = dept_by_code(dept_code)
        if dept is None:
            return None
        prog = db.session.execute(
            db.select(AcademicProgram).where(
                AcademicProgram.department_id == dept.id,
                AcademicProgram.name == program_name)).scalars().first()
        if prog is None:
            prog = db.session.execute(
                db.select(AcademicProgram).where(
                    AcademicProgram.department_id == dept.id)).scalars().first()
        return prog

    # --- 3. Distribute students across all departments ------------------ #
    for number, first, last, dob, gender, dept_code, program_name, year, nat in JAVA_STUDENTS:
        dept = dept_by_code(dept_code)
        prog = program_for(dept_code, program_name)
        if dept is None or prog is None:
            continue
        email = f"{number.lower()}@usamis.demo"
        admission_year = 2026 - year + 1
        student, created = _get_or_create(Student, {
            "first_name": first, "last_name": last, "email": email,
            "department_id": dept.id, "program_id": prog.id,
            "admission_date": dt.date(admission_year, 9, 1),
            "enrollment_status": "active",
        }, student_number=number)
        # Backfill missing contact details (idempotent).
        if not student.date_of_birth:
            try:
                student.date_of_birth = dt.date.fromisoformat(dob)
            except ValueError:
                pass
        if not student.phone:
            student.phone = f"+8613800{number[-4:]}"
        if created:
            report["students_created"] += 1
        else:
            # Re-distribute an existing student that is still stuck in one dept.
            if student.department_id != dept.id:
                student.department_id = dept.id
                student.program_id = prog.id
                report["students_redistributed"] += 1
    db.session.commit()

    # --- 3b. Distribute the Python cohort across ALL JIT departments ----- #
    # The user asked for the student body to be spread across every department
    # we have in the Python project, not concentrated in Software Engineering.
    report.update(_distribute_across_departments())
    db.session.commit()

    # --- 4. Courses + offerings ----------------------------------------- #
    sem1 = db.session.execute(
        db.select(Semester).where(Semester.academic_year == "2024/2025",
                                  Semester.term == "fall")).scalars().first()
    sem2 = db.session.execute(
        db.select(Semester).where(Semester.academic_year == "2024/2025",
                                  Semester.term == "spring")).scalars().first()
    sem_by_no = {1: sem1, 2: sem2}

    courses: dict[str, Course] = {}
    for code, title, dept_code, credits, capacity, sem_no, status in JAVA_COURSES:
        dept = dept_by_code(dept_code)
        if dept is None:
            continue
        course, created = _get_or_create(Course, {
            "title": title, "credits": credits, "department_id": dept.id,
            "is_active": status == "active",
            "description": f"{title} (imported from Java reference roster).",
        }, code=code)
        courses[code] = course
        if created:
            report["courses_created"] += 1
    db.session.commit()

    for code, course in courses.items():
        meta = next(c for c in JAVA_COURSES if c[0] == code)
        sem = sem_by_no.get(meta[5])
        if sem is None:
            continue
        offering, created = _get_or_create(CourseOffering, {
            "capacity": meta[4], "is_active": True},
            course_id=course.id, semester_id=sem.id)
        if created:
            report["offerings_created"] += 1
        db.session.commit()
        # Enrol the students whose department matches this course's department.
        for number, *_rest in [(s[0],) for s in JAVA_STUDENTS]:
            student = db.session.execute(
                db.select(Student).where(Student.student_number == number)).scalars().first()
            if student and student.department_id == course.department_id:
                existing = db.session.execute(
                    db.select(Enrollment).where(
                        Enrollment.student_id == student.id,
                        Enrollment.offering_id == offering.id)).scalars().first()
                if existing is None:
                    enr = Enrollment(student_id=student.id, offering_id=offering.id,
                                     status="enrolled")
                    db.session.add(enr)
                    db.session.flush()
                    report["enrollments_created"] += 1
                    # A published grade so the GPA/report pages have data.
                    base = 62 + (student.id * 5 + course.id * 3) % 34
                    letter = ("A" if base >= 85 else "B" if base >= 75
                              else "C" if base >= 65 else "D" if base >= 60 else "F")
                    db.session.add(Grade(
                        enrollment_id=enr.id, student_id=student.id,
                        score=Decimal(f"{base}.00"), letter=letter,
                        is_published=True,
                        published_at=dt.datetime.now(dt.timezone.utc)))
                    report["grades_created"] += 1
    db.session.commit()

    # --- 5. Fee records (Java: per-student tuition/accommodation) ------- #
    tuition, _ = _get_or_create(FeeCategory, {
        "name": "Tuition", "default_amount": Decimal("12000.00"), "is_active": True},
        code="TUITION")
    registration, _ = _get_or_create(FeeCategory, {
        "name": "Registration", "default_amount": Decimal("2000.00"), "is_active": True},
        code="REGISTRATION")
    lab, _ = _get_or_create(FeeCategory, {
        "name": "Laboratory", "default_amount": Decimal("1500.00"), "is_active": True},
        code="LAB")
    db.session.commit()

    # The Java roster's fee spread, applied to the Java students.
    java_fee_profile = {
        "STU2024001": [(tuition, Decimal("12000.00"), Decimal("12000.00"))],
        "STU2024002": [(tuition, Decimal("12000.00"), Decimal("8000.00"))],
        "STU2024003": [(tuition, Decimal("12000.00"), Decimal("0.00"))],
        "STU2024004": [(tuition, Decimal("18000.00"), Decimal("18000.00"))],
        "STU2024005": [(registration, Decimal("5000.00"), Decimal("5000.00"))],
        "STU2024008": [(tuition, Decimal("12000.00"), Decimal("6000.00"))],
    }
    if sem1 is not None:
        for number, entries in java_fee_profile.items():
            student = db.session.execute(
                db.select(Student).where(Student.student_number == number)).scalars().first()
            if student is None:
                continue
            for cat, total, paid in entries:
                assessment = db.session.execute(
                    db.select(FeeAssessment).where(
                        FeeAssessment.student_id == student.id,
                        FeeAssessment.category_id == cat.id,
                        FeeAssessment.semester_id == sem1.id)).scalars().first()
                if assessment is None:
                    db.session.add(FeeAssessment(
                        student_id=student.id, category_id=cat.id, semester_id=sem1.id,
                        amount=total, adjustment=Decimal("0.00"),
                        due_date=dt.date(2024, 10, 15)))
                    report["fees_created"] += 1
                if paid > 0:
                    ref = f"JAVA-{number[-4:]}-{cat.code}"
                    exists = db.session.execute(
                        db.select(Payment).where(Payment.student_id == student.id,
                                                 Payment.reference == ref)).scalars().first()
                    if exists is None:
                        db.session.add(Payment(
                            student_id=student.id, amount=paid, reference=ref,
                            paid_on=dt.date(2024, 9, 20)))
    db.session.commit()
    return report


# --------------------------------------------------------------------------- #
# Whole-cohort department distribution
# --------------------------------------------------------------------------- #
# Programmes used when moving a student into a department that has one.
def _distribute_across_departments() -> dict:
    """Spread the student body evenly across every active department.

    Idempotent: only reassigns when a department would otherwise be empty, and
    stabilises after a couple of runs because the counts converge.
    """
    out = {"students_distributed": 0}
    departments = list(db.session.execute(
        db.select(Department).where(Department.is_active.is_(True))
        .order_by(Department.code)).scalars())
    if not departments:
        return out

    def count_for(dept_id: int) -> int:
        return db.session.scalar(
            db.select(db.func.count(Student.id)).where(Student.department_id == dept_id)) or 0

    # Only general academic departments should hold a student body; skip the
    # pure service units (Physical Education / General Education) which teach
    # everyone but do not enrol their own cohort.
    skip_codes = {"0402", "0501"}
    academic = [d for d in departments if d.code not in skip_codes]
    if not academic:
        return out

    def default_program(dept_id: int):
        return db.session.execute(
            db.select(AcademicProgram).where(AcademicProgram.department_id == dept_id)
            .order_by(AcademicProgram.id)).scalars().first()

    # Donors: departments with more than one student (we move the surplus).
    donors = sorted(academic, key=lambda d: count_for(d.id), reverse=True)
    for dept in academic:
        if count_for(dept.id) > 0:
            continue
        # Find a donor with a surplus to move one student out of.
        donor = next((d for d in donors if count_for(d.id) > 1), None)
        if donor is None:
            break
        student = db.session.execute(
            db.select(Student).where(Student.department_id == donor.id)
            .order_by(Student.id)).scalars().first()
        if student is None:
            continue
        prog = default_program(dept.id)
        student.department_id = dept.id
        if prog is not None:
            student.program_id = prog.id
        out["students_distributed"] += 1
    return out
