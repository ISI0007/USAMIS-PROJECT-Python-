"""Semester and offering forms."""
from flask_wtf import FlaskForm
from wtforms import BooleanField, DateField, IntegerField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class SemesterForm(FlaskForm):
    academic_year = StringField("Academic Year", validators=[DataRequired(), Length(max=16)])
    term = SelectField("Term", choices=[("fall", "Fall"), ("spring", "Spring"), ("summer", "Summer")])
    start_date = DateField("Start Date", validators=[Optional()])
    end_date = DateField("End Date", validators=[Optional()])
    is_active = BooleanField("Active", default=True)
    registration_open = BooleanField("Registration Open", default=True)
    submit = SubmitField("Save Semester")


class OfferingForm(FlaskForm):
    course_id = SelectField("Course", coerce=int, validators=[DataRequired()], choices=[])
    teacher_id = SelectField("Teacher", coerce=int, validators=[Optional()], choices=[])
    capacity = IntegerField("Capacity", validators=[DataRequired(), NumberRange(min=1, max=1000)],
                            default=40)
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save Offering")
