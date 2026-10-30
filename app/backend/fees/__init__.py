"""Fee management: categories, assessments, payments and balances."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import (
    FeeAssessment, FeeCategory, Payment, Semester, Student,
)
from ..security.decorators import permission_required
from ..services import fee_service
from .forms import AssessmentForm, FeeCategoryForm, PaymentForm

bp = Blueprint("fees", __name__, url_prefix="/fees")


@bp.route("/")
@login_required
@permission_required("manage_fees")
def index():
    page = request.args.get("page", 1, type=int)
    pagination = db.paginate(
        db.select(FeeAssessment).order_by(FeeAssessment.created_at.desc()),
        page=page, per_page=15, error_out=False,
    )
    categories = db.session.execute(db.select(FeeCategory).order_by(FeeCategory.code)).scalars().all()
    return render_template("fees/index.html", pagination=pagination, categories=categories)


@bp.route("/categories/new", methods=["GET", "POST"])
@login_required
@permission_required("manage_fees")
def create_category():
    form = FeeCategoryForm()
    if form.validate_on_submit():
        if db.session.execute(
            db.select(FeeCategory).where(FeeCategory.code == form.code.data.strip().upper())
        ).scalars().first():
            flash("That category code already exists.", "danger")
        else:
            cat = FeeCategory(
                code=form.code.data.strip().upper(),
                name=form.name.data.strip(),
                description=form.description.data.strip() if form.description.data else None,
                default_amount=form.default_amount.data,
                is_active=form.is_active.data,
            )
            db.session.add(cat)
            db.session.commit()
            from ..services import audit
            audit.log_action("fee_category_created", "FeeCategory", cat.id,
                             summary=f"Created {cat.code}")
            db.session.commit()
            flash("Fee category created.", "success")
            return redirect(url_for("fees.index"))
    return render_template("fees/category_form.html", form=form)


@bp.route("/assess", methods=["GET", "POST"])
@login_required
@permission_required("manage_fees")
def assess():
    form = AssessmentForm()
    _assess_choices(form)
    if form.validate_on_submit():
        student = db.session.get(Student, form.student_id.data)
        category = db.session.get(FeeCategory, form.category_id.data)
        semester = db.session.get(Semester, form.semester_id.data) if form.semester_id.data else None
        if student is None or category is None:
            abort(404)
        try:
            fee_service.assess_fee(
                current_user, student, category, form.amount.data,
                semester=semester, adjustment=form.adjustment.data,
                due_date=form.due_date.data, note=form.note.data or "",
            )
            flash("Fee assessed.", "success")
            return redirect(url_for("fees.index"))
        except fee_service.FeeError as exc:
            flash(str(exc), "danger")
    return render_template("fees/assess_form.html", form=form)


@bp.route("/pay", methods=["GET", "POST"])
@login_required
@permission_required("manage_fees")
def pay():
    form = PaymentForm()
    _assess_choices(form)
    if form.validate_on_submit():
        student = db.session.get(Student, form.student_id.data)
        if student is None:
            abort(404)
        assessment = db.session.get(FeeAssessment, form.assessment_id.data) \
            if form.assessment_id.data else None
        try:
            fee_service.record_payment(
                current_user, student, form.amount.data, assessment=assessment,
                reference=form.reference.data or "", paid_on=form.paid_on.data,
                note=form.note.data or "",
            )
            flash("Payment recorded.", "success")
            return redirect(url_for("fees.index"))
        except fee_service.FeeError as exc:
            flash(str(exc), "danger")
    return render_template("fees/pay_form.html", form=form)


@bp.route("/student/<int:student_id>")
@login_required
def student_fees(student_id: int):
    student = db.session.get(Student, student_id)
    if student is None:
        abort(404)

    if current_user.role == "student":
        own = db.session.execute(
            db.select(Student).where(Student.user_id == current_user.id)
        ).scalars().first()
        if own is None or own.id != student.id:
            abort(403)
    elif not current_user.has_permission("manage_fees"):
        abort(403)

    assessments = db.session.execute(
        db.select(FeeAssessment).where(FeeAssessment.student_id == student.id)
    ).scalars().all()
    payments = db.session.execute(
        db.select(Payment).where(Payment.student_id == student.id)
        .order_by(Payment.paid_on.desc())
    ).scalars().all()
    balance = fee_service.student_balance(student)
    return render_template("fees/student.html", student=student, assessments=assessments,
                           payments=payments, balance=balance)


@bp.route("/my")
@login_required
@permission_required("view_own_fees")
def my_fees():
    student = db.session.execute(
        db.select(Student).where(Student.user_id == current_user.id)
    ).scalars().first()
    if student is None:
        return render_template("dashboard/no_profile.html")
    return redirect(url_for("fees.student_fees", student_id=student.id))


def _assess_choices(form) -> None:
    form.student_id.choices = [
        (s.id, f"{s.student_number} — {s.full_name}")
        for s in db.session.execute(db.select(Student).order_by(Student.student_number)).scalars().all()
    ]
    if hasattr(form, "category_id"):
        form.category_id.choices = [
            (c.id, f"{c.code} — {c.name}")
            for c in db.session.execute(db.select(FeeCategory).order_by(FeeCategory.code)).scalars().all()
        ]
    if hasattr(form, "semester_id"):
        form.semester_id.choices = [(0, "— none —")] + [
            (s.id, s.label)
            for s in db.session.execute(db.select(Semester).order_by(Semester.academic_year.desc())).scalars().all()
        ]
    if hasattr(form, "assessment_id"):
        form.assessment_id.choices = [(0, "— none —")] + [
            (a.id, f"#{a.id} {a.category.code} {a.amount}")
            for a in db.session.execute(db.select(FeeAssessment)).scalars().all()
        ]
