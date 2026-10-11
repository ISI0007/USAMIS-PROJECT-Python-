"""Attendance forms."""
from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Optional


class AttendanceForm(FlaskForm):
    session_date = DateField("Session Date", validators=[DataRequired()])
    status = SelectField("Status", choices=[
        ("present", "Present"), ("absent", "Absent"),
        ("late", "Late"), ("excused", "Excused"),
    ])
    note = TextAreaField("Note", validators=[Optional()])
    submit = SubmitField("Record Attendance")
