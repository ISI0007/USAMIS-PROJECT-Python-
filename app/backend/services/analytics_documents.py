"""Management analytics reports as letterhead PDF + editable DOCX + on-screen views.

Every figure is derived from live database rows. Where a value is not present in
the schema, the report shows "—" rather than fabricating it.

Reports:
  * Revenue Summary     -- fee records grouped by fee type (billed/collected/outstanding)
  * Course Pass Rate    -- pass/fail rate per course offering
  * At-Risk Students    -- low attendance AND/OR low average
  * GPA Transcripts     -- per-student GPA, program, year, status
  * Enrollment Summary  -- enrollment counts by status / course / department
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import func

from ..extensions import db
from ..models import (
    AcademicProgram, Attendance, Course, CourseOffering, Department, Enrollment,
    FeeAssessment, FeeCategory, Grade, Payment, Student,
)
from ..services import report_documents as report_docs


def _generated_on() -> str:
    return dt.datetime.now().strftime("%d %b %Y, %H:%M")


# --------------------------------------------------------------------------- #
# Grade helpers
# --------------------------------------------------------------------------- #
_GRADE_POINTS = {
    "A+": 4.0, "A": 4.0, "A-": 3.7,
    "B+": 3.3, "B": 3.0, "B-": 2.7,
    "C+": 2.3, "C": 2.0, "C-": 1.7,
    "D+": 1.3, "D": 1.0, "F": 0.0,
}
_PASS_LETTERS = {"A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D"}


def _published_grades():
    """Published grades joined through enrollment to their offering's course."""
    return db.session.execute(
        db.select(Grade.letter, Grade.student_id, Enrollment.offering_id,
                  CourseOffering.course_id, Course.code, Course.title)
        .join(Enrollment, Enrollment.id == Grade.enrollment_id)
        .join(CourseOffering, CourseOffering.id == Enrollment.offering_id)
        .join(Course, Course.id == CourseOffering.course_id)
        .where(Grade.is_published.is_(True))
    ).all()


def _year_of_study(student) -> str:
    """Derive year of study from admission date; '—' if unknown."""
    if not student or not student.admission_date:
        return "—"
    years = max(dt.date.today().year - student.admission_date.year + 1, 1)
    return f"Year {years}"


def _status_label(student) -> str:
    value = getattr(student, "enrollment_status", None)
    return (value or "—").capitalize() if value else "—"


# --------------------------------------------------------------------------- #
# 1. Revenue Summary (by fee type)
# --------------------------------------------------------------------------- #
def revenue_summary_doc():
    rows_sql = db.session.execute(
        db.select(
            FeeCategory.name,
            func.count(FeeAssessment.id),
            func.sum(FeeAssessment.amount - FeeAssessment.adjustment),
        )
        .join(FeeCategory, FeeCategory.id == FeeAssessment.category_id)
        .group_by(FeeCategory.name)
        .order_by(func.sum(FeeAssessment.amount - FeeAssessment.adjustment).desc())
    ).all()

    # payments mapped to the category of their assessment
    collected_by_cat: dict = {}
    paid_rows = db.session.execute(
        db.select(FeeAssessment.category_id, Payment.amount)
        .join(Payment, Payment.assessment_id == FeeAssessment.id)
    ).all()
    cat_names = {c.id: c.name for c in db.session.execute(db.select(FeeCategory)).scalars()}
    for cat_id, amount in paid_rows:
        name = cat_names.get(cat_id)
        collected_by_cat[name] = collected_by_cat.get(name, 0.0) + float(amount or 0)

    rows = []
    total_billed = total_collected = 0.0
    for name, count, billed in rows_sql:
        billed_f = float(billed or 0)
        collected = collected_by_cat.get(name, 0.0)
        outstanding = billed_f - collected
        total_billed += billed_f
        total_collected += collected
        rows.append([name, str(count), f"{billed_f:,.0f}",
                     f"{collected:,.0f}", f"{outstanding:,.0f}"])
    total_outstanding = max(total_billed - total_collected, 0.0)
    rate = (total_collected / total_billed * 100.0) if total_billed else 0.0

    doc = report_docs.ReportDoc(
        title="Revenue Summary",
        subtitle=f"{sum(int(r[1]) for r in rows)} fee records · billed, collected and outstanding by fee type.",
        reference=report_docs._ref("RS"),
        generated_on=_generated_on(),
        totals=[
            ("Billed", f"¥{total_billed:,.0f}"),
            ("Collected", f"¥{total_collected:,.0f}"),
            ("Outstanding", f"¥{total_outstanding:,.0f}"),
            ("Collection rate", f"{rate:.1f}%"),
        ],
        tables=[{
            "heading": "Revenue by fee type",
            "columns": ["Fee Type", "Records", "Billed", "Collected", "Outstanding"],
            "rows": rows,
        }],
    )
    return doc


# --------------------------------------------------------------------------- #
# 2. Course Pass Rate
# --------------------------------------------------------------------------- #
def course_pass_rate_doc():
    agg: dict = {}
    meta: dict = {}
    for letter, _sid, offering_id, _cid, code, title in _published_grades():
        slot = agg.setdefault(offering_id, {"pass": 0, "fail": 0})
        if letter in _PASS_LETTERS:
            slot["pass"] += 1
        elif letter in _GRADE_POINTS:
            slot["fail"] += 1
        else:
            continue
        meta[offering_id] = (code, title)

    rows = []
    for offering_id, slot in agg.items():
        total = slot["pass"] + slot["fail"]
        if not total:
            continue
        code, title = meta.get(offering_id, ("—", "—"))
        rate = slot["pass"] / total * 100.0
        rows.append([code, title, str(slot["pass"]), str(slot["fail"]),
                     str(total), f"{rate:.1f}%"])
    rows.sort(key=lambda r: float(r[5].rstrip("%")))

    tot = sum(s["pass"] + s["fail"] for s in agg.values())
    pas = sum(s["pass"] for s in agg.values())
    doc = report_docs.ReportDoc(
        title="Course Pass Rate",
        subtitle="Proportion of published grades at pass level, per course offering.",
        reference=report_docs._ref("PR"),
        generated_on=_generated_on(),
        totals=[
            ("Offerings with grades", len(rows)),
            ("Overall pass rate", f"{(pas / tot * 100.0) if tot else 0.0:.1f}%"),
            ("Grades counted", tot),
        ],
        tables=[{
            "heading": "Pass rate by course",
            "columns": ["Course", "Title", "Pass", "Fail", "Total", "Pass rate"],
            "rows": rows,
        }],
    )
    return doc


# --------------------------------------------------------------------------- #
# 3. At-Risk Students
# --------------------------------------------------------------------------- #
def at_risk_doc():
    att = db.session.execute(
        db.select(
            Attendance.student_id,
            func.count(Attendance.id),
            func.sum(db.case((Attendance.status.in_(("present", "late")), 1), else_=0)),
        ).group_by(Attendance.student_id)
    ).all()
    att_rate: dict = {}
    for sid, total, present in att:
        if total:
            att_rate[sid] = (present or 0) / total

    grades_by_student: dict = {}
    for letter, sid, *_rest in _published_grades():
        pts = _GRADE_POINTS.get(letter)
        if pts is not None:
            grades_by_student.setdefault(sid, []).append(pts)

    rows = []
    for student in db.session.execute(db.select(Student)).scalars().all():
        reasons = []
        rate = att_rate.get(student.id)
        if rate is not None and rate < 0.75:
            reasons.append(f"Attendance {rate * 100:.1f}%")
        pts = grades_by_student.get(student.id)
        avg = sum(pts) / len(pts) if pts else None
        if avg is not None and avg < 2.0:
            reasons.append(f"Average {avg:.2f}")
        if reasons:
            prog = student.program.code if student.program else "—"
            rows.append([student.student_number, student.full_name, prog,
                         f"{rate * 100:.1f}%" if rate is not None else "—",
                         f"{avg:.2f}" if avg is not None else "—",
                         "; ".join(reasons)])
    rows.sort(key=lambda r: r[1])

    doc = report_docs.ReportDoc(
        title="At-Risk Students",
        subtitle="Students below 75% attendance and/or below a 2.00 average.",
        reference=report_docs._ref("AR"),
        generated_on=_generated_on(),
        totals=[("At-risk students", len(rows))],
        tables=[{
            "heading": "At-risk students",
            "columns": ["Student No.", "Name", "Program", "Attendance", "Average", "Flags"],
            "rows": rows,
        }],
    )
    return doc


# --------------------------------------------------------------------------- #
# 4. GPA Transcripts
# --------------------------------------------------------------------------- #
def gpa_transcripts_doc():
    per_student: dict = {}
    for letter, sid, *_rest in _published_grades():
        per_student.setdefault(sid, []).append(_GRADE_POINTS.get(letter))

    rows = []
    for student in db.session.execute(db.select(Student)).scalars().all():
        pts = [p for p in per_student.get(student.id, []) if p is not None]
        gpa = f"{sum(pts) / len(pts):.2f}" if pts else "—"
        prog = student.program.name if student.program else "—"
        rows.append([student.student_number, student.full_name, prog,
                     _year_of_study(student), gpa, _status_label(student)])
    rows.sort(key=lambda r: r[0])

    gpas = [float(r[4]) for r in rows if r[4] != "—"]
    doc = report_docs.ReportDoc(
        title="GPA Transcripts",
        subtitle=f"{len(rows)} students · grade-point average (4.00 scale) from published grades.",
        reference=report_docs._ref("GP"),
        generated_on=_generated_on(),
        totals=[
            ("Students", len(rows)),
            ("Students with a GPA", len(gpas)),
            ("Institution average GPA", f"{sum(gpas) / len(gpas):.2f}" if gpas else "—"),
        ],
        tables=[{
            "heading": "Student GPA",
            "columns": ["Student No.", "Name", "Program", "Year", "GPA", "Status"],
            "rows": rows,
        }],
    )
    return doc


# --------------------------------------------------------------------------- #
# 5. Enrollment Summary
# --------------------------------------------------------------------------- #
def enrollment_summary_doc():
    by_status = db.session.execute(
        db.select(Enrollment.status, func.count(Enrollment.id))
        .group_by(Enrollment.status).order_by(Enrollment.status)
    ).all()
    by_course = db.session.execute(
        db.select(Course.code, func.count(Enrollment.id))
        .join(CourseOffering, CourseOffering.course_id == Course.id)
        .join(Enrollment, Enrollment.offering_id == CourseOffering.id)
        .group_by(Course.code).order_by(Course.code)
    ).all()
    by_department = db.session.execute(
        db.select(Department.code, Department.name, func.count(Student.id))
        .join(Student, Student.department_id == Department.id, isouter=True)
        .group_by(Department.code, Department.name).order_by(Department.code)
    ).all()

    total_enr = db.session.scalar(db.select(func.count(Enrollment.id))) or 0
    total_stu = db.session.scalar(db.select(func.count(Student.id))) or 0

    doc = report_docs.ReportDoc(
        title="Enrollment Summary",
        subtitle="Enrollment counts by status, course and department.",
        reference=report_docs._ref("EN"),
        generated_on=_generated_on(),
        totals=[
            ("Total enrollments", total_enr),
            ("Total students", total_stu),
            ("Courses enrolled", len(by_course)),
        ],
        tables=[
            {"heading": "Enrollment by Status",
             "columns": ["Status", "Count"],
             "rows": [[s, c] for s, c in by_status]},
            {"heading": "Enrollment by Course",
             "columns": ["Course", "Enrollments"],
             "rows": [[code, c] for code, c in by_course]},
            {"heading": "Students by Department",
             "columns": ["Code", "Department", "Students"],
             "rows": [[code, name, c] for code, name, c in by_department]},
        ],
    )
    return doc
