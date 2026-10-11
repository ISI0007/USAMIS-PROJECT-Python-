"""Reports and management analytics (database-derived, no fabricated data)."""
from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func

from ..extensions import db
from ..models import (
    Attendance, Course, CourseOffering, Department, Enrollment, FeeAssessment,
    Grade, Payment, Student,
)
from ..security.decorators import permission_required

bp = Blueprint("reports", __name__, url_prefix="/reports")


@bp.route("/")
@login_required
@permission_required("view_reports")
def index():
    students_per_department = db.session.execute(
        db.select(Department.code, func.count(Student.id))
        .join(Student, Student.department_id == Department.id, isouter=True)
        .group_by(Department.code)
        .order_by(Department.code)
    ).all()

    enrollment_by_status = db.session.execute(
        db.select(Enrollment.status, func.count(Enrollment.id))
        .group_by(Enrollment.status)
    ).all()

    grade_distribution = db.session.execute(
        db.select(Grade.letter, func.count(Grade.id))
        .where(Grade.is_published.is_(True))
        .group_by(Grade.letter)
        .order_by(Grade.letter)
    ).all()

    totals = {
        "students": db.session.scalar(db.select(func.count(Student.id))) or 0,
        "courses": db.session.scalar(db.select(func.count(Course.id))) or 0,
        "offerings": db.session.scalar(db.select(func.count(CourseOffering.id))) or 0,
        "assessed": db.session.scalar(
            db.select(func.coalesce(func.sum(FeeAssessment.amount - FeeAssessment.adjustment), 0))
        ) or 0,
        "collected": db.session.scalar(db.select(func.coalesce(func.sum(Payment.amount), 0))) or 0,
    }
    totals["outstanding"] = max(float(totals["assessed"]) - float(totals["collected"]), 0.0)

    return render_template(
        "reports/index.html",
        students_per_department=students_per_department,
        enrollment_by_status=enrollment_by_status,
        grade_distribution=grade_distribution,
        totals=totals,
    )


@bp.route("/fee-defaulters")
@login_required
@permission_required("view_reports")
def fee_defaulters():
    """Students whose assessed fees exceed recorded payments."""
    assessed = db.session.execute(
        db.select(FeeAssessment.student_id,
                  func.sum(FeeAssessment.amount - FeeAssessment.adjustment))
        .group_by(FeeAssessment.student_id)
    ).all()
    paid_rows = dict(db.session.execute(
        db.select(Payment.student_id, func.sum(Payment.amount))
        .group_by(Payment.student_id)
    ).all())

    defaulters = []
    for student_id, total in assessed:
        paid = float(paid_rows.get(student_id, 0) or 0)
        outstanding = float(total or 0) - paid
        if outstanding > 0:
            student = db.session.get(Student, student_id)
            defaulters.append({
                "student": student,
                "outstanding": round(outstanding, 2),
            })
    defaulters.sort(key=lambda r: r["outstanding"], reverse=True)
    return render_template("reports/defaulters.html", defaulters=defaulters)


@bp.route("/low-attendance")
@login_required
@permission_required("view_reports")
def low_attendance():
    """Attendance summary per student per offering (below a documented threshold)."""
    rows = db.session.execute(
        db.select(
            Attendance.student_id,
            Attendance.offering_id,
            func.count(Attendance.id).label("total"),
            func.sum(db.case((Attendance.status.in_(("present", "late")), 1), else_=0)).label("present"),
        ).group_by(Attendance.student_id, Attendance.offering_id)
    ).all()

    summary = []
    for student_id, offering_id, total, present in rows:
        if not total:
            continue
        rate = present / total
        if rate < 0.75:
            summary.append({
                "student": db.session.get(Student, student_id),
                "offering": db.session.get(CourseOffering, offering_id),
                "total": int(total),
                "present": int(present or 0),
                "rate": round(rate * 100, 1),
            })
    summary.sort(key=lambda r: r["rate"])
    return render_template("reports/attendance.html", summary=summary)
