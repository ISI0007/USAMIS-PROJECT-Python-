"""Reports and management analytics (database-derived, no fabricated data)."""
import io
import os

from flask import Blueprint, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from ..extensions import db
from ..models import (
    Attendance, Course, CourseOffering, Department, Enrollment, FeeAssessment,
    Grade, Payment, Student,
)
from ..security.decorators import permission_required

bp = Blueprint("reports", __name__, url_prefix="/reports")

# --------------------------------------------------------------------------- #
# PDF export
# --------------------------------------------------------------------------- #
# A report page is rendered to PDF via Playwright/Chromium (already a project
# dependency for screenshots). The PDF is streamed as a download. If the
# browser engine is unavailable the route returns 503 rather than a corrupt
# file, so the failure is honest and visible.
def _render_pdf(relative_url: str, download_name: str, *, landscape: bool = False):
    from flask import current_app, url_for

    base = current_app.config.get("PDF_BASE_URL")
    if not base:
        # Prefer the local bind the server actually listens on; request.url_root
        # is correct for browser-originated requests but can be "localhost"
        # (which may not resolve to the running server).
        host = os.environ.get("FLASK_RUN_HOST", "127.0.0.1")
        port = os.environ.get("FLASK_RUN_PORT", "5000")
        base = f"http://{host}:{port}"
    target = base.rstrip("/") + relative_url

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - optional dependency
        current_app.logger.warning("PDF export unavailable: %s", exc)
        return "", 503

    # Carry the authenticated session so the printed page is authorized.
    cookie_header = request.headers.get("Cookie", "")
    pdf_bytes = b""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(
                extra_http_headers={"Cookie": cookie_header} if cookie_header else {},
            )
            page = context.new_page()
            page.goto(target, wait_until="networkidle", timeout=30000)
            page.emulate_media(media="print")
            pdf_bytes = page.pdf(
                format="A4",
                landscape=landscape,
                print_background=True,
                margin={"top": "14mm", "bottom": "14mm", "left": "12mm", "right": "12mm"},
            )
            browser.close()
    except Exception as exc:  # pragma: no cover - runtime dependent
        current_app.logger.warning("PDF render failed: %s", exc)
        return "", 503

    if not pdf_bytes:
        return "", 503
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=download_name,
    )


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


@bp.route("/pdf")
@login_required
@permission_required("view_reports")
def index_pdf():
    """Download the Management Reports overview as a PDF."""
    return _render_pdf(url_for("reports.index"), "usamis-management-reports.pdf")


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


@bp.route("/fee-defaulters/pdf")
@login_required
@permission_required("view_reports")
def fee_defaulters_pdf():
    """Download the Fee Defaulters report as a PDF."""
    return _render_pdf(
        url_for("reports.fee_defaulters"), "usamis-fee-defaulters.pdf"
    )


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


@bp.route("/low-attendance/pdf")
@login_required
@permission_required("view_reports")
def low_attendance_pdf():
    """Download the Low Attendance report as a PDF."""
    return _render_pdf(
        url_for("reports.low_attendance"), "usamis-low-attendance.pdf"
    )
