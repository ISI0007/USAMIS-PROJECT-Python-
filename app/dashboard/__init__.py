"""Role-specific dashboards.

All statistics are derived from the database — never hardcoded.
"""
from flask import Blueprint, render_template
from flask_login import current_user, login_required
from sqlalchemy import func

from ..extensions import db
from ..models import (
    AcademicProgram, Attendance, Course, CourseOffering, Department, Enrollment,
    FeeAssessment, Grade, Payment, Semester, Student, Teacher,
)
from ..security.permissions import Role
from ..services import fee_service

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


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
    for o in offerings:
        enrolled = sum(1 for e in o.enrollments if e.status in ("enrolled", "completed"))
        graded = sum(1 for e in o.enrollments
                     if e.grade is not None and e.grade.is_published)
        rows.append({"offering": o, "enrolled": enrolled, "graded": graded})
    return render_template("dashboard/teacher.html", rows=rows, teacher=teacher)


def _finance_dashboard():
    total_fees = db.session.scalar(
        db.select(func.coalesce(func.sum(FeeAssessment.amount - FeeAssessment.adjustment), 0))
    ) or 0
    total_paid = db.session.scalar(db.select(func.coalesce(func.sum(Payment.amount), 0))) or 0
    outstanding = max(float(total_fees) - float(total_paid), 0.0)
    recent = db.session.execute(
        db.select(Payment).order_by(Payment.created_at.desc()).limit(10)
    ).scalars().all()
    return render_template(
        "dashboard/finance.html",
        stats={"fees_assessed": total_fees, "fees_paid": total_paid,
               "outstanding": outstanding},
        recent=recent,
    )


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

    balance = fee_service.student_balance(student)

    return render_template(
        "dashboard/student.html",
        student=student,
        enrollments=enrollments,
        grades=published_grades,
        performance=performance,
        attendance_total=len(attendance_rows),
        attendance_present=present,
        balance=balance,
    )
