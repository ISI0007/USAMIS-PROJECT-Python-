"""Reports and management analytics (database-derived, no fabricated data)."""
import datetime as dt
import io
import os

from flask import Blueprint, render_template, request, send_file, url_for, abort
from flask_login import current_user, login_required
from sqlalchemy import func

from ..extensions import db
from ..models import (
    Attendance, Course, CourseOffering, Department, Enrollment, FeeAssessment,
    Grade, Payment, Student,
)
from ..security.decorators import permission_required
from ..services import report_documents as report_docs
from ..services import analytics_documents as analytics_docs

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
        report_registry=_report_registry(),
    )


def _report_registry() -> dict:
    """Cards shown on the Reports page (mirrors the Java reports view)."""
    analytics = {
        "revenue-summary": ("Revenue Summary", "Billed vs collected by fee type"),
        "course-pass-rate": ("Course Pass Rate", "Analysis of student performance"),
        "at-risk": ("Academic Risk", "Students below the risk threshold"),
        "gpa-transcripts": ("GPA Transcripts", "Per-student GPA summary"),
        "enrollment-summary": ("Enrollment Summary", "By status, course and department"),
    }
    registry: dict = {}
    for slug, (title, subtitle) in analytics.items():
        registry[slug] = {
            "title": title, "subtitle": subtitle,
            "pdf_url": url_for("reports.analytics_pdf", slug=slug),
            "docx_url": url_for("reports.analytics_docx", slug=slug),
        }
    registry["fee-defaulters"] = {
        "title": "Fee Defaulters List", "subtitle": "Students with outstanding balances",
        "pdf_url": url_for("reports.fee_defaulters_pdf"),
        "docx_url": url_for("reports.fee_defaulters_docx"),
    }
    registry["low-attendance"] = {
        "title": "Low Attendance", "subtitle": "Below the 75% attendance threshold",
        "pdf_url": url_for("reports.low_attendance_pdf"),
        "docx_url": url_for("reports.low_attendance_docx"),
    }
    registry["overview"] = {
        "title": "Management Overview", "subtitle": "Institution-wide totals and breakdowns",
        "pdf_url": url_for("reports.index_pdf"),
        "docx_url": url_for("reports.index_docx"),
    }
    registry["students-per-dept"] = {
        "title": "Students per Department", "subtitle": "Distribution across all departments",
        "pdf_url": url_for("reports.index_pdf"), "docx_url": "",
    }
    return registry


@bp.route("/_render/<slug>")
@login_required
@permission_required("view_reports")
def render_fragment(slug):
    """Return a small HTML fragment for the on-page report card (fetch target)."""
    builder = _ANALYTICS.get(slug, (None, None, None))[0] if slug in _ANALYTICS else None
    if builder is not None:
        doc = builder()
    elif slug == "fee-defaulters":
        doc, _name = _fee_defaulters_doc()
    elif slug == "low-attendance":
        doc, _name = _low_attendance_doc()
    elif slug in ("overview", "students-per-dept"):
        doc = _management_overview_doc()
    else:
        abort(404)
    return render_template("reports/_fragment.html", doc=doc)


@bp.route("/pdf")
@login_required
@permission_required("view_reports")
def index_pdf():
    """Download the Management Reports overview as a letterhead PDF."""
    doc = _management_overview_doc()
    return send_file(
        io.BytesIO(report_docs.build_pdf(doc)),
        mimetype="application/pdf", as_attachment=True,
        download_name=f"{doc.reference}.pdf",
    )


@bp.route("/docx")
@login_required
@permission_required("view_reports")
def index_docx():
    """Download the Management Reports overview as an editable Word file."""
    doc = _management_overview_doc()
    return send_file(
        io.BytesIO(report_docs.build_docx(doc)),
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True, download_name=f"{doc.reference}.docx",
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


@bp.route("/fee-defaulters/pdf")
@login_required
@permission_required("view_reports")
def fee_defaulters_pdf():
    """Download the Fee Defaulters report as a letterhead PDF."""
    doc, name = _fee_defaulters_doc()
    return send_file(
        io.BytesIO(report_docs.build_pdf(doc)),
        mimetype="application/pdf", as_attachment=True,
        download_name=f"{name}.pdf",
    )


@bp.route("/fee-defaulters/docx")
@login_required
@permission_required("view_reports")
def fee_defaulters_docx():
    """Download the Fee Defaulters report as an editable Word file."""
    doc, name = _fee_defaulters_doc()
    return send_file(
        io.BytesIO(report_docs.build_docx(doc)),
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True, download_name=f"{name}.docx",
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
    """Download the Low Attendance report as a letterhead PDF."""
    doc, name = _low_attendance_doc()
    return send_file(
        io.BytesIO(report_docs.build_pdf(doc)),
        mimetype="application/pdf", as_attachment=True,
        download_name=f"{name}.pdf",
    )


@bp.route("/low-attendance/docx")
@login_required
@permission_required("view_reports")
def low_attendance_docx():
    """Download the Low Attendance report as an editable Word file."""
    doc, name = _low_attendance_doc()
    return send_file(
        io.BytesIO(report_docs.build_docx(doc)),
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True, download_name=f"{name}.docx",
    )


# --------------------------------------------------------------------------- #
# Additional analytics reports (Revenue, Pass Rate, At-Risk, GPA, Enrollment)
# --------------------------------------------------------------------------- #
_ANALYTICS = {
    "revenue-summary": (analytics_docs.revenue_summary_doc, "reports/revenue_summary.html",
                        "Revenue Summary"),
    "course-pass-rate": (analytics_docs.course_pass_rate_doc, "reports/pass_rate.html",
                         "Course Pass Rate"),
    "at-risk": (analytics_docs.at_risk_doc, "reports/at_risk.html", "At-Risk Students"),
    "gpa-transcripts": (analytics_docs.gpa_transcripts_doc, "reports/gpa.html", "GPA Transcripts"),
    "enrollment-summary": (analytics_docs.enrollment_summary_doc, "reports/enrollment.html",
                           "Enrollment Summary"),
}


def _analytics_download(slug, fmt):
    builder, _tpl, _title = _ANALYTICS[slug]
    doc = builder()
    if fmt == "pdf":
        payload = report_docs.build_pdf(doc)
        mimetype = "application/pdf"
    else:
        payload = report_docs.build_docx(doc)
        mimetype = ("application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document")
    return send_file(
        io.BytesIO(payload), mimetype=mimetype, as_attachment=True,
        download_name=f"{doc.reference}.{fmt}",
    )


@bp.route("/<slug>")
@login_required
@permission_required("view_reports")
def analytics_view(slug):
    """On-screen view for each analytics report."""
    if slug not in _ANALYTICS:
        abort(404)
    builder, tpl, title = _ANALYTICS[slug]
    doc = builder()
    return render_template(tpl, doc=doc, slug=slug, report_title=title)


@bp.route("/<slug>/pdf")
@login_required
@permission_required("view_reports")
def analytics_pdf(slug):
    if slug not in _ANALYTICS:
        abort(404)
    return _analytics_download(slug, "pdf")


@bp.route("/<slug>/docx")
@login_required
@permission_required("view_reports")
def analytics_docx(slug):
    if slug not in _ANALYTICS:
        abort(404)
    return _analytics_download(slug, "docx")


# --------------------------------------------------------------------------- #
# Report document builders (letterhead PDF + editable DOCX share these)
# --------------------------------------------------------------------------- #
def _generated_on() -> str:
    return dt.datetime.now().strftime("%d %b %Y, %H:%M")


def _management_overview_doc():
    students_per_department = db.session.execute(
        db.select(Department.code, Department.name, func.count(Student.id))
        .join(Student, Student.department_id == Department.id, isouter=True)
        .group_by(Department.code, Department.name)
        .order_by(Department.code)
    ).all()
    enrollment_by_status = db.session.execute(
        db.select(Enrollment.status, func.count(Enrollment.id))
        .group_by(Enrollment.status).order_by(Enrollment.status)
    ).all()
    grade_distribution = db.session.execute(
        db.select(Grade.letter, func.count(Grade.id))
        .where(Grade.is_published.is_(True))
        .group_by(Grade.letter).order_by(Grade.letter)
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

    doc = report_docs.ReportDoc(
        title="Management Reports",
        subtitle="Institution-wide totals and breakdowns, derived from live data.",
        reference=report_docs._ref("MR"),
        generated_on=_generated_on(),
        totals=[
            ("Students", totals["students"]),
            ("Courses", totals["courses"]),
            ("Course offerings", totals["offerings"]),
            ("Fees assessed", f"{float(totals['assessed']):,.2f}"),
            ("Fees collected", f"{float(totals['collected']):,.2f}"),
            ("Outstanding", f"{float(totals['outstanding']):,.2f}"),
        ],
        tables=[
            {
                "heading": "Students per Department",
                "columns": ["Code", "Department", "Students"],
                "rows": [[c, n, cnt] for c, n, cnt in students_per_department],
            },
            {
                "heading": "Enrollment by Status",
                "columns": ["Status", "Count"],
                "rows": [[s, cnt] for s, cnt in enrollment_by_status],
            },
            {
                "heading": "Published Grade Distribution",
                "columns": ["Letter", "Count"],
                "rows": [[l, cnt] for l, cnt in grade_distribution],
            },
        ],
    )
    return doc


def _fee_defaulters_doc():
    assessed = db.session.execute(
        db.select(FeeAssessment.student_id,
                  func.sum(FeeAssessment.amount - FeeAssessment.adjustment))
        .group_by(FeeAssessment.student_id)
    ).all()
    paid_rows = dict(db.session.execute(
        db.select(Payment.student_id, func.sum(Payment.amount))
        .group_by(Payment.student_id)
    ).all())
    rows = []
    total_outstanding = 0.0
    for student_id, total in assessed:
        paid = float(paid_rows.get(student_id, 0) or 0)
        outstanding = float(total or 0) - paid
        if outstanding > 0:
            student = db.session.get(Student, student_id)
            prog = student.program.code if student and student.program else "—"
            rows.append([student.student_number, student.full_name, prog, f"{outstanding:,.2f}"])
            total_outstanding += outstanding
    rows.sort(key=lambda r: float(r[3].replace(",", "")), reverse=True)
    doc = report_docs.ReportDoc(
        title="Fee Defaulters Report",
        subtitle="Students with an outstanding fee balance (assessed fees minus payments).",
        reference=report_docs._ref("FD"),
        generated_on=_generated_on(),
        totals=[("Students with a balance", len(rows)),
                ("Total outstanding", f"{total_outstanding:,.2f}")],
        tables=[{
            "heading": "Defaulters",
            "columns": ["Student No.", "Name", "Program", "Outstanding"],
            "rows": rows,
        }],
    )
    return doc, doc.reference


def _low_attendance_doc():
    rows_raw = db.session.execute(
        db.select(
            Attendance.student_id,
            Attendance.offering_id,
            func.count(Attendance.id).label("total"),
            func.sum(db.case((Attendance.status.in_(("present", "late")), 1), else_=0)).label("present"),
        ).group_by(Attendance.student_id, Attendance.offering_id)
    ).all()
    rows = []
    for student_id, offering_id, total, present in rows_raw:
        if not total:
            continue
        rate = present / total
        if rate < 0.75:
            student = db.session.get(Student, student_id)
            offering = db.session.get(CourseOffering, offering_id)
            rows.append([student.student_number, student.full_name,
                         offering.course.code, int(present or 0), int(total),
                         f"{rate * 100:.1f}%"])
    rows.sort(key=lambda r: float(r[5].rstrip("%")))
    doc = report_docs.ReportDoc(
        title="Low Attendance Report",
        subtitle="Students below the 75% attendance threshold, by course.",
        reference=report_docs._ref("LA"),
        generated_on=_generated_on(),
        totals=[("Records below threshold", len(rows))],
        tables=[{
            "heading": "Low attendance",
            "columns": ["Student No.", "Name", "Course", "Present", "Total", "Rate"],
            "rows": rows,
        }],
    )
    return doc, doc.reference
