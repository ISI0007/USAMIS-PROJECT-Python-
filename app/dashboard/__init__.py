"""Role-specific dashboards.

All statistics are derived from the database — never hardcoded.
"""
from flask import Blueprint, render_template
from flask_login import current_user, login_required
from sqlalchemy import func

from ..extensions import db
from ..models import (
    AcademicProgram, Attendance, AuditLog, Course, CourseOffering, Department,
    Enrollment, FeeAssessment, Grade, Payment, Semester, Student, Teacher,
)
from ..security.permissions import Role
from ..services import fee_service
from ..services import prediction_service

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")

# Grade band labels used for the distribution chart (letters are stored on
# published grades; see the grading policy in docs/ALGORITHMS.md).
GRADE_BANDS = ("A", "B", "C", "D", "F")


def _grade_distribution() -> list[int]:
    """Count published grades per letter band (A-F)."""
    rows = db.session.execute(
        db.select(Grade.letter, func.count(Grade.id))
        .where(Grade.is_published.is_(True))
        .group_by(Grade.letter)
    ).all()
    counts = {letter: 0 for letter in GRADE_BANDS}
    for letter, n in rows:
        if letter in counts:
            counts[letter] = n
    return [counts[b] for b in GRADE_BANDS]


def _students_by_department() -> tuple[list[str], list[int]]:
    """Student counts grouped by department name."""
    rows = db.session.execute(
        db.select(Department.name, func.count(Student.id))
        .join(Student, Student.department_id == Department.id, isouter=True)
        .group_by(Department.name)
        .order_by(func.count(Student.id).desc())
    ).all()
    labels = [name for name, _ in rows]
    values = [n for _, n in rows]
    return labels, values


def _enrollment_trend() -> tuple[list[str], list[int]]:
    """Active enrollments per semester, ordered chronologically.

    ``Semester.label`` is a Python property (not a mapped column), so the
    label is composed in Python from the mapped columns.
    """
    rows = db.session.execute(
        db.select(
            Semester.academic_year,
            Semester.term,
            Semester.start_date,
            func.count(Enrollment.id),
        )
        .join(CourseOffering, CourseOffering.semester_id == Semester.id, isouter=True)
        .join(Enrollment, Enrollment.offering_id == CourseOffering.id, isouter=True)
        .where(Enrollment.status.in_(("enrolled", "completed")))
        .group_by(Semester.id, Semester.academic_year, Semester.term, Semester.start_date)
        .order_by(Semester.start_date)
    ).all()
    labels = [f"{year} {term.title()}" for year, term, _start, _n in rows]
    values = [n for _year, _term, _start, n in rows]
    return labels, values


@bp.route("/")
@login_required
def home():
    role = current_user.role
    if role == Role.ADMIN:
        return _admin_dashboard()
    if role == Role.ACADEMIC_STAFF:
        return _staff_dashboard()
    if role == Role.TEACHER:
        return _teacher_dashboard()
    if role == Role.FINANCE:
        return _finance_dashboard()
    if role == Role.PARENT:
        return _parent_dashboard()
    return _student_dashboard()


def _active_semester():
    return db.session.execute(
        db.select(Semester).where(Semester.is_active.is_(True)).order_by(Semester.start_date.desc())
    ).scalars().first()


def _admin_dashboard():
    total_students = db.session.scalar(db.select(func.count(Student.id))) or 0
    active_departments = db.session.scalar(
        db.select(func.count(Department.id)).where(Department.is_active.is_(True))
    ) or 0
    active_programs = db.session.scalar(
        db.select(func.count(AcademicProgram.id)).where(AcademicProgram.is_active.is_(True))
    ) or 0
    offerings = db.session.scalar(
        db.select(func.count(CourseOffering.id)).where(CourseOffering.is_active.is_(True))
    ) or 0
    enrolled = db.session.scalar(
        db.select(func.count(Enrollment.id)).where(Enrollment.status.in_(("enrolled", "completed")))
    ) or 0
    pending = db.session.scalar(
        db.select(func.count(Enrollment.id)).where(Enrollment.status == "pending")
    ) or 0

    total_fees = db.session.scalar(
        db.select(func.coalesce(func.sum(FeeAssessment.amount - FeeAssessment.adjustment), 0))
    ) or 0
    total_paid = db.session.scalar(db.select(func.coalesce(func.sum(Payment.amount), 0))) or 0
    outstanding = max(float(total_fees) - float(total_paid), 0.0)

    dept_labels, dept_values = _students_by_department()
    trend_labels, trend_values = _enrollment_trend()
    recent_activity = db.session.execute(
        db.select(AuditLog).order_by(AuditLog.created_at.desc()).limit(8)
    ).scalars().all()

    return render_template(
        "dashboard/admin.html",
        stats={
            "students": total_students,
            "departments": active_departments,
            "programs": active_programs,
            "offerings": offerings,
            "enrolled": enrolled,
            "pending": pending,
            "fees_assessed": total_fees,
            "fees_paid": total_paid,
            "outstanding": outstanding,
        },
        semester=_active_semester(),
        charts={
            "dept_labels": dept_labels,
            "dept_values": dept_values,
            "trend_labels": trend_labels,
            "trend_values": trend_values,
            "grade_labels": list(GRADE_BANDS),
            "grade_values": _grade_distribution(),
            "fee_assessed": float(total_fees),
            "fee_paid": float(total_paid),
        },
        recent_activity=recent_activity,
    )


def _staff_dashboard():
    pending = db.session.execute(
        db.select(Enrollment).where(Enrollment.status == "pending")
        .order_by(Enrollment.requested_at.desc()).limit(10)
    ).scalars().all()
    counts = {
        "students": db.session.scalar(db.select(func.count(Student.id))) or 0,
        "courses": db.session.scalar(db.select(func.count(Course.id))) or 0,
        "offerings": db.session.scalar(db.select(func.count(CourseOffering.id))) or 0,
    }
    return render_template("dashboard/staff.html", pending=pending, counts=counts,
                           semester=_active_semester())


def _teacher_dashboard():
    teacher = db.session.execute(
        db.select(Teacher).where(Teacher.user_id == current_user.id)
    ).scalars().first()
    offerings = []
    if teacher:
        offerings = db.session.execute(
            db.select(CourseOffering).where(CourseOffering.teacher_id == teacher.id)
        ).scalars().all()
    rows = []
    pending_publication = 0
    incomplete_attendance = 0
    for o in offerings:
        enrolled = sum(1 for e in o.enrollments if e.status in ("enrolled", "completed"))
        graded = sum(1 for e in o.enrollments
                     if e.grade is not None and e.grade.is_published)
        ungraded = max(enrolled - graded, 0)
        pending_publication += ungraded
        sessions = db.session.scalar(
            db.select(func.count(func.distinct(Attendance.session_date)))
            .where(Attendance.offering_id == o.id)
        ) or 0
        if enrolled and sessions == 0:
            incomplete_attendance += 1
        rows.append({"offering": o, "enrolled": enrolled, "graded": graded,
                     "ungraded": ungraded})
    return render_template(
        "dashboard/teacher.html", rows=rows, teacher=teacher,
        pending_publication=pending_publication,
        incomplete_attendance=incomplete_attendance,
    )


def _finance_dashboard():
    total_fees = db.session.scalar(
        db.select(func.coalesce(func.sum(FeeAssessment.amount - FeeAssessment.adjustment), 0))
    ) or 0
    total_paid = db.session.scalar(db.select(func.coalesce(func.sum(Payment.amount), 0))) or 0
    outstanding = max(float(total_fees) - float(total_paid), 0.0)
    recent = db.session.execute(
        db.select(Payment).order_by(Payment.created_at.desc()).limit(10)
    ).scalars().all()
    collection_pct = (float(total_paid) / float(total_fees) * 100.0) if total_fees else 0.0
    return render_template(
        "dashboard/finance.html",
        stats={"fees_assessed": total_fees, "fees_paid": total_paid,
               "outstanding": outstanding, "collection_pct": round(collection_pct, 1)},
        recent=recent,
    )


def _parent_dashboard():
    """Parent landing: the linked students with a headline risk band each."""
    from ..services import parent_service, prediction_service

    children = parent_service.linked_students(current_user)
    rows = []
    for student in children:
        prediction, signals = prediction_service.predict_for_student(student)
        rows.append({
            "student": student,
            "prediction": prediction,
            "average": signals["weighted_average"],
            "attendance_rate": signals["attendance_rate"],
        })
    return render_template("dashboard/parent.html", rows=rows)


def _student_dashboard():
    student = db.session.execute(
        db.select(Student).where(Student.user_id == current_user.id)
    ).scalars().first()
    if student is None:
        return render_template("dashboard/no_profile.html")

    enrollments = db.session.execute(
        db.select(Enrollment).where(Enrollment.student_id == student.id)
        .order_by(Enrollment.requested_at.desc())
    ).scalars().all()

    published_grades = [e.grade for e in enrollments
                        if e.grade is not None and e.grade.is_published]

    from ..algorithms.academic_performance import calculate_performance
    performance = calculate_performance([
        {
            "course_code": e.offering.course.code,
            "credits": e.offering.course.credits,
            "score": e.grade.score,
            "published": e.grade.is_published,
        }
        for e in enrollments if e.grade is not None
    ])

    attendance_rows = db.session.execute(
        db.select(Attendance).where(Attendance.student_id == student.id)
    ).scalars().all()
    present = sum(1 for a in attendance_rows if a.status in ("present", "late"))
    attendance_pct = round((present / len(attendance_rows) * 100.0), 1) if attendance_rows else 0.0

    balance = fee_service.student_balance(student)

    # F4 — explainable academic-risk prediction from stored grades + attendance.
    prediction, _signals = prediction_service.predict_for_student(student)

    # Current-semester active courses (distinct from full history).
    active_sem = _active_semester()
    current_enrollments = [
        e for e in enrollments
        if e.status in ("enrolled", "pending")
        and (active_sem is None or e.offering.semester_id == active_sem.id)
    ]

    return render_template(
        "dashboard/student.html",
        student=student,
        enrollments=enrollments,
        current_enrollments=current_enrollments,
        grades=published_grades,
        performance=performance,
        attendance_total=len(attendance_rows),
        attendance_present=present,
        attendance_pct=attendance_pct,
        balance=balance,
        semester=active_sem,
        prediction=prediction,
    )
