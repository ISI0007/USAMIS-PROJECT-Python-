"""Enrollment forms."""
from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField
from wtforms.validators import DataRequired


class EnrollmentRequestForm(FlaskForm):
    offering_id = SelectField("Course Offering", coerce=int, validators=[DataRequired()],
                              choices=[])
    submit = SubmitField("Check Eligibility & Apply")
