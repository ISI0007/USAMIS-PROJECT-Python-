"""Synthetic development/demo data generation.

SAFETY:
* Development/demo use only — synthetic data, never real student records.
* Idempotent: repeated runs upsert on natural keys and do not duplicate.
* ``--reset`` clears the demo tables first (explicit, deliberate action).

The curriculum mirrors a real 4-year / 8-semester Software Engineering
undergraduate programme (see docs/CURRICULUM.md). Student roll numbers follow
the institutional pattern ``G<YY><2224><8601><NN>`` for the 2024 intake cohort,
i.e. G19 -> G2422486019 ... G26 -> G2422486026.
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
    ParentLink,
    Payment,
    PaymentIntent,
    Prerequisite,
    Semester,
    Student,
    Teacher,
    User,
)

DEMO_PASSWORD = "Demo_Pass1!"  # noqa: S105 - documented demo credential

# --------------------------------------------------------------------------- #
# Cohorts (roll numbers) and identities
# --------------------------------------------------------------------------- #
# Roll number pattern: G + 2-digit suffix + 2224 + 860 + 2-digit roll
ROLL_PREFIX = "G24224860"

STUDENTS = [
    # (roll suffix, first_name, last_name, gender-neutral email local part)
    ("G19", "Lin", "Wei"),
    ("G20", "Chen", "Yu"),
    ("G21", "Zhang", "Hao"),
    ("G22", "Wang", "Fang"),
    ("G23", "Liu", "Yang"),
    ("G24", "Zhao", "Min"),
    ("G25", "Sun", "Lei"),
    ("G26", "Zhou", "Xin"),
]


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
        PaymentIntent, Payment, FeeAssessment, FeeCategory, Attendance, Grade,
        Enrollment, Prerequisite, CourseOffering, Semester, Course,
        AcademicProgram, ParentLink, Student, Teacher, Department, AuditLog, User,
    ):
        db.session.query(model).delete()
    db.session.commit()


# --------------------------------------------------------------------------- #
# Curriculum: 8 semesters of a Software Engineering programme
# (code, title, credits, category, component, is_core)
# --------------------------------------------------------------------------- #
CURRICULUM: dict[int, list[tuple]] = {
    1: [
        ("070112051L", "Advanced Mathematics 1", 3, "General Education", "Course", False),
        ("050110201L", "Comprehensive Chinese 1", 6, "General Education", "Course", False),
        ("050111101L", "Overview of China", 2, "General Education", "Course", False),
        ("050110211L", "Chinese Traditional Culture 1", 1.5, "General Education", "Course", False),
        ("040212627L", "Physical Education 1", 1.5, "General Education", "Course", False),
        ("080931201L", "Advanced Language Programming", 2.5, "Professional Foundation", "Course", True),
        ("080931202L", "Advanced Language Programming Lab", 2, "Professional Foundation", "Course", False),
    ],
    2: [
        ("070112052L", "Advanced Mathematics 2", 3, "General Education", "Course", False),
        ("050110202L", "Comprehensive Chinese 2", 6, "General Education", "Course", False),
        ("050110212L", "Chinese Traditional Culture 2", 1.5, "General Education", "Course", False),
        ("040212628L", "Physical Education 2", 1.5, "General Education", "Course", False),
        ("080931204L", "Advanced Java Programming", 3, "Major", "Course", True),
        ("080931205L", "Data Structures and Algorithms", 4, "Major", "Course", True),
    ],
    3: [
        ("070112053L", "Linear Algebra C", 3, "General Education", "Course", False),
        ("050110203L", "Comprehensive Chinese 3", 6, "General Education", "Course", False),
        ("050110213L", "Chinese Traditional Culture 3", 1.5, "General Education", "Course", False),
        ("040212629L", "Physical Education 3", 1.5, "General Education", "Course", False),
        ("080931203L", "Introduction to Software Engineering", 3, "Professional Foundation", "Course", True),
        ("080941201L", "Python Programming", 3, "Major", "Course", False),
        ("080941202L", "Robotics Technology", 3, "Major", "Course", False),
        ("080991201L", "Comprehensive Programming Course Design", 1, "Practical Teaching", "Practical", False),
    ],
    4: [
        ("070112054L", "Probability Theory & Mathematical Statistics C", 3, "General Education", "Course", False),
        ("050110204L", "Comprehensive Chinese 4", 6, "General Education", "Course", False),
        ("050110214L", "Chinese Traditional Culture 4", 1.5, "General Education", "Course", False),
        ("040212630L", "Physical Education 4", 1.5, "General Education", "Course", False),
        ("080931206L", "Operating Systems", 4, "Major", "Course", True),
        ("080931208L", "Software Requirements & Modeling", 3, "Major", "Course", True),
    ],
    5: [
        ("050110221L", "Chinese Reading 1", 2, "General Education", "Course", False),
        ("080931211L", "Database Systems", 3, "Professional Foundation", "Course", True),
        ("080931209L", "Software Architecture", 3, "Major", "Course", True),
        ("080931210L", "Introduction to Artificial Intelligence", 2, "Major", "Course", False),
        ("080931207L", "Computer Networks", 3, "Major", "Course", False),
    ],
    6: [
        ("050110222L", "Chinese Reading 2", 2, "General Education", "Course", False),
        ("080931215L", "Software Testing", 3, "Major", "Course", True),
        ("080931216L", "Software Project Management", 2, "Major", "Course", False),
        ("080931214L", "Web Development and Applications", 4, "Major", "Course", True),
        ("080941203L", "GPU Parallel Programming", 3, "Major", "Course", False),
        ("080991203L", "Information Systems Course Design", 1, "Practical Teaching", "Practical", False),
        ("080991204L", "Computer Network Course Design", 1, "Practical Teaching", "Practical", False),
    ],
    7: [
        ("080931217L", "Academic Paper Writing", 2, "General Education", "Course", False),
        ("080941204L", "Web Front-end Design and Development", 3, "Major", "Course", False),
        ("080991206L", "Project Practice", 8, "Practical Teaching", "Practical", False),
        ("080991205L", "Software Testing Course Design", 1, "Practical Teaching", "Practical", False),
    ],
    8: [
        ("080991207L", "Graduation Thesis (Design)", 15, "Practical Teaching", "Practical", False),
    ],
}

# Prerequisites expressed as (course_code, required_course_code, min_grade)
PREREQUISITES = [
    ("070112052L", "070112051L", Decimal("60.00")),   # Adv Maths 2 <- Adv Maths 1
    ("080931205L", "080931201L", Decimal("60.00")),   # Data Structures <- Adv Language Prog
    ("080931206L", "080931205L", Decimal("60.00")),   # Operating Systems <- Data Structures
    ("080931211L", "080931205L", Decimal("60.00")),   # Database Systems <- Data Structures
    ("080931209L", "080931203L", Decimal("60.00")),   # Software Architecture <- Intro SE
    ("080931215L", "080931203L", Decimal("60.00")),   # Software Testing <- Intro SE
    ("080931214L", "080931203L", Decimal("60.00")),   # Web Development <- Intro SE
]


def run_seed(reset: bool = False) -> None:
    if reset:
        _reset()

    # --- Departments ---------------------------------------------------- #
    cse, _ = _get_or_create(
        Department,
        {"name": "Software Engineering", "is_active": True,
         "description": "Software engineering, systems and applications."},
        code="0809",
    )
    gen, _ = _get_or_create(
        Department,
        {"name": "General Education", "is_active": True,
         "description": "Mathematics, languages and general studies."},
        code="0501",
    )
    pe, _ = _get_or_create(
        Department,
        {"name": "Physical Education", "is_active": True,
         "description": "Physical education and health."},
        code="0402",
    )
    db.session.commit()

    # --- Programs ------------------------------------------------------- #
    bse, _ = _get_or_create(
        AcademicProgram,
        {"name": "BSc Software Engineering", "department_id": cse.id,
         "duration_years": 4, "total_credits_required": 137, "is_active": True},
        code="BSE",
    )
    db.session.commit()

    # --- Users ---------------------------------------------------------- #
    def account(username, email, name, role):
        user, _ = _get_or_create(
            User,
            {"email": email, "full_name": name, "role": role,
             "status": "active", "is_active_flag": True,
             "password_hash": generate_password_hash(DEMO_PASSWORD)},
            username=username,
        )
        return user

    admin = account("admin", "admin@usamis.demo", "System Administrator", "administrator")
    registrar = account("registrar", "registrar@usamis.demo", "Registrar Office", "academic_staff")
    finance = account("finance", "finance@usamis.demo", "Finance Officer", "finance")
    teacher_user = account("t.mensah", "t.mensah@usamis.demo", "Thomas Mensah", "teacher")
    teacher_user2 = account("a.okafor", "a.okafor@usamis.demo", "Ada Okafor", "teacher")
    # Primary demo student account (roll G19).
    student_user = account("s.demo", "g2422486019@usamis.demo", "Lin Wei", "student")
    # F5 — demo parent/guardian account (linked to two children below).
    parent_user = account("p.wei", "parent@usamis.demo", "Wei JianGuo", "parent")
    db.session.commit()

    # --- Teachers ------------------------------------------------------- #
    t1, _ = _get_or_create(Teacher, {
        "first_name": "Thomas", "last_name": "Mensah", "email": teacher_user.email,
        "department_id": cse.id, "user_id": teacher_user.id}, staff_number="T-1001")
    t2, _ = _get_or_create(Teacher, {
        "first_name": "Ada", "last_name": "Okafor", "email": teacher_user2.email,
        "department_id": gen.id, "user_id": teacher_user2.id}, staff_number="T-1002")
    db.session.commit()

    # --- Students (roll G19..G26) --------------------------------------- #
    students: list[Student] = []
    for roll, first, last in STUDENTS:
        number = f"{ROLL_PREFIX}{roll[1:]}"          # G19 -> G2422486019
        email = f"{number.lower()}@usamis.demo"
        # Deterministic demo phone numbers so SMS notifications are exercisable.
        phone = f"+8613800{roll[1:].zfill(6)}"
        student, _ = _get_or_create(Student, {
            "first_name": first, "last_name": last, "email": email,
            "phone": phone,
            "department_id": cse.id, "program_id": bse.id,
            "admission_date": dt.date(2024, 9, 1), "enrollment_status": "active"},
            student_number=number,
        )
        # Backfill a phone number for students seeded before phones existed.
        if not student.phone:
            student.phone = phone
        # Link the primary demo login (s.demo) to the first student (G19).
        if roll == "G19" and student.user_id is None:
            student.user_id = student_user.id
        students.append(student)
    db.session.commit()

    # --- Courses (full curriculum) -------------------------------------- #
    # Map programme component -> department for realistic ownership.
    dept_for = {"0809": cse, "0501": gen, "0402": pe, "0701": gen}
    courses: dict[str, Course] = {}
    for sem_no in sorted(CURRICULUM):
        for code, title, credits, category, component, is_core in CURRICULUM[sem_no]:
            dept = dept_for.get(code[:4], cse)
            course, _ = _get_or_create(Course, {
                "title": title,
                "credits": credits,
                "department_id": dept.id,
                "is_active": True,
                "description": f"{title} — {category} ({component}"
                               f"{', core' if is_core else ''}).",
            }, code=code)
            courses[code] = course
    db.session.commit()

    # --- Prerequisites -------------------------------------------------- #
    for course_code, req_code, min_grade in PREREQUISITES:
        c = courses.get(course_code)
        r = courses.get(req_code)
        if not c or not r:
            continue
        _get_or_create(Prerequisite, {"min_grade": min_grade},
                       course_id=c.id, required_course_id=r.id)
    db.session.commit()

    # --- Semesters (8, matching the curriculum years) ------------------- #
    # 2024/2025 (sem 1-2), 2025/2026 (sem 3-4), 2026/2027 (sem 5-6),
    # 2027/2028 (sem 7-8). Terms alternate fall/spring.
    # (term, start_month, start_day, end_month, end_day)
    SEMESTER_SHAPE = {
        "fall": (9, 1, 12, 20),
        "spring": (2, 15, 6, 30),
    }
    semesters: dict[int, Semester] = {}
    years = [(2024, 2025), (2025, 2026), (2026, 2027), (2027, 2028)]
    sem_no = 1
    for start_year, end_year in years:
        for term in ("fall", "spring"):
            if sem_no > 8:
                break
            sm, sd, em, ed = SEMESTER_SHAPE[term]
            # Fall runs in the first calendar year; spring spills into the next.
            start_date = dt.date(start_year, sm, sd)
            end_date = dt.date(start_year if term == "fall" else end_year, em, ed)
            label = f"{start_year}/{end_year}"
            semester, _ = _get_or_create(Semester, {
                "start_date": start_date,
                "end_date": end_date,
                "is_active": True,
                "registration_open": True,
            }, academic_year=label, term=term)
            semesters[sem_no] = semester
            sem_no += 1
    db.session.commit()

    # --- Offerings (every curriculum course in its semester) ------------ #
    offerings: dict[tuple[int, str], CourseOffering] = {}
    for sem_no, rows in CURRICULUM.items():
        semester = semesters.get(sem_no)
        if semester is None:
            continue
        for idx, (code, *_rest) in enumerate(rows):
            course = courses.get(code)
            if course is None:
                continue
            offering, _ = _get_or_create(CourseOffering, {
                "teacher_id": (t1 if idx % 2 == 0 else t2).id,
                "capacity": 60, "is_active": True},
                course_id=course.id, semester_id=semester.id,
            )
            offerings[(sem_no, code)] = offering
    db.session.commit()

    # --- Enrollments, grades, attendance -------------------------------- #
    # Enrol everyone (G19..G26) across the first five semesters so the
    # dashboards, trend charts and transcript pages show a real-looking load.
    # The most recent semester is left as pending/review requests so the
    # registrar "Pending Requests" queue is populated.
    ATT_STATUSES = ("present", "present", "present", "late", "absent", "excused")
    for s in students:
        # G26 (newest intake) only has first-semester history.
        sems = (1,) if s.student_number.endswith("26") else (1, 2, 3, 4, 5)
        for sem_no in sems:
            for idx, (code, *_rest) in enumerate(CURRICULUM.get(sem_no, [])):
                offering = offerings.get((sem_no, code))
                if offering is None:
                    continue
                # Most recent semester for non-final students: pending requests.
                is_latest = (sem_no == max(sems)) and (s.student_number[-2:] not in ("26",))
                status = "pending" if (is_latest and idx % 3 == 0) else "enrolled"
                existing = db.session.execute(
                    db.select(Enrollment).where(
                        Enrollment.student_id == s.id,
                        Enrollment.offering_id == offering.id,
                        Enrollment.status.in_(("enrolled", "pending")))
                ).scalars().first()
                if existing:
                    continue
                enrollment = Enrollment(student_id=s.id, offering_id=offering.id,
                                        status=status)
                db.session.add(enrollment)
                db.session.flush()

                if status != "enrolled":
                    continue
                grade = db.session.execute(
                    db.select(Grade).where(Grade.enrollment_id == enrollment.id)
                ).scalars().first()
                if grade is None:
                    # Deterministic, realistic spread of scores (55..92).
                    base = 55 + (s.id * 7 + idx * 11 + sem_no * 3) % 38
                    score = Decimal(f"{base}.00")
                    letter = ("A" if score >= 85 else "B" if score >= 75
                              else "C" if score >= 65 else "D" if score >= 60 else "F")
                    db.session.add(Grade(
                        enrollment_id=enrollment.id, student_id=s.id, score=score,
                        letter=letter, is_published=True,
                        published_at=dt.datetime.now(dt.timezone.utc),
                        entered_by_id=(teacher_user if idx % 2 == 0 else teacher_user2).id))

                # Four session dates with a realistic attendance mix.
                for d_idx, day in enumerate((dt.date(2025, 9, 8),
                                             dt.date(2025, 9, 15),
                                             dt.date(2025, 9, 22),
                                             dt.date(2025, 9, 29))):
                    exists = db.session.execute(
                        db.select(Attendance).where(
                            Attendance.student_id == s.id,
                            Attendance.offering_id == offering.id,
                            Attendance.session_date == day)
                    ).scalars().first()
                    if not exists:
                        db.session.add(Attendance(
                            student_id=s.id, offering_id=offering.id, session_date=day,
                            status=ATT_STATUSES[(s.id + idx + d_idx) % len(ATT_STATUSES)],
                            recorded_by_id=teacher_user.id))
    db.session.commit()

    # --- Fees ----------------------------------------------------------- #
    tuition, _ = _get_or_create(FeeCategory, {
        "name": "Tuition", "default_amount": Decimal("12000.00"), "is_active": True},
        code="TUITION")
    library, _ = _get_or_create(FeeCategory, {
        "name": "Library", "default_amount": Decimal("300.00"), "is_active": True},
        code="LIBRARY")
    accommodation, _ = _get_or_create(FeeCategory, {
        "name": "Accommodation", "default_amount": Decimal("1200.00"), "is_active": True},
        code="ACCOMM")
    db.session.commit()

    sem1 = semesters.get(1)
    for s in students:
        for cat, amt in ((tuition, Decimal("12000.00")),
                         (library, Decimal("300.00")),
                         (accommodation, Decimal("1200.00"))):
            assessment = db.session.execute(
                db.select(FeeAssessment).where(
                    FeeAssessment.student_id == s.id,
                    FeeAssessment.category_id == cat.id,
                    FeeAssessment.semester_id == sem1.id)
            ).scalars().first()
            if assessment is None:
                db.session.add(FeeAssessment(
                    student_id=s.id, category_id=cat.id, semester_id=sem1.id,
                    amount=amt, adjustment=Decimal("0.00"),
                    due_date=dt.date(2024, 10, 15), created_by_id=finance.id))

        # A realistic spread of payments: full, partial and none outstanding.
        # suffix decides the payer profile so the fee views differ per student.
        suffix = s.student_number[-2:]
        payments_for = {
            "19": [("PAY-DEMO-0001", Decimal("5000.00"), dt.date(2024, 9, 20))],
            "20": [("PAY-DEMO-0020", Decimal("12000.00"), dt.date(2024, 9, 25))],
            "21": [("PAY-DEMO-0021", Decimal("6300.00"), dt.date(2024, 10, 2))],
            "22": [("PAY-DEMO-0022", Decimal("13500.00"), dt.date(2024, 9, 30))],
            "23": [("PAY-DEMO-0023", Decimal("300.00"), dt.date(2024, 10, 5))],
            "24": [("PAY-DEMO-0024", Decimal("8000.00"), dt.date(2024, 10, 8))],
        }
        for ref, amt, paid_on in payments_for.get(suffix, []):
            existing_pay = db.session.execute(
                db.select(Payment).where(Payment.student_id == s.id,
                                         Payment.reference == ref)
            ).scalars().first()
            if existing_pay is None:
                db.session.add(Payment(
                    student_id=s.id, amount=amt, reference=ref, paid_on=paid_on,
                    recorded_by_id=finance.id))
    db.session.commit()

    # --- Audit seed marker ---------------------------------------------- #
    if db.session.query(AuditLog).count() == 0:
        db.session.add(AuditLog(
            actor_id=admin.id, actor_username="admin", action="seed",
            entity_type="System", entity_id=None,
            summary="Synthetic demo data generated (8-semester SE curriculum, "
                    "students G19-G26)."))
        db.session.commit()

    # --- F5 parent links ------------------------------------------------ #
    # The demo guardian (p.wei) is linked to two children (G19 and G21).
    child_rolls = {"19": "father", "21": "father"}
    for s in students:
        suffix = s.student_number[-2:]
        if suffix in child_rolls:
            _get_or_create(ParentLink, {
                "relationship_type": child_rolls[suffix],
                "is_active": True,
            }, parent_user_id=parent_user.id, student_id=s.id)
    db.session.commit()
