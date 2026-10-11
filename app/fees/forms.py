"""Fee forms."""
import datetime as dt

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField, DateField, DecimalField, SelectField, StringField, SubmitField, TextAreaField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class FeeCategoryForm(FlaskForm):
    code = StringField("Code", validators=[DataRequired(), Length(max=24)])
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=1000)])
    default_amount = DecimalField("Default Amount", places=2,
                                  validators=[DataRequired(), NumberRange(min=0)])
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save Category")


class AssessmentForm(FlaskForm):
    student_id = SelectField("Student", coerce=int, validators=[DataRequired()], choices=[])
    category_id = SelectField("Fee Category", coerce=int, validators=[DataRequired()], choices=[])
    semester_id = SelectField("Semester", coerce=int, validators=[Optional()],
                              choices=[(0, "— none —")])
    amount = DecimalField("Amount", places=2, validators=[DataRequired(), NumberRange(min=0)])
    adjustment = DecimalField("Adjustment / Waiver", places=2,
                              validators=[Optional(), NumberRange(min=0)], default=0)
    due_date = DateField("Due Date", validators=[Optional()])
    note = TextAreaField("Note", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Record Assessment")


class PaymentForm(FlaskForm):
    student_id = SelectField("Student", coerce=int, validators=[DataRequired()], choices=[])
    assessment_id = SelectField("Applies To", coerce=int, validators=[Optional()],
                                choices=[(0, "— none —")])
    amount = DecimalField("Amount", places=2, validators=[DataRequired(), NumberRange(min=0.01)])
    reference = StringField("Reference", validators=[Optional(), Length(max=48)])
    paid_on = DateField("Paid On", validators=[Optional()], default=dt.date.today)
    note = TextAreaField("Note", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Record Payment")
