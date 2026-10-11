"""Student forms."""
from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional

STATUS_CHOICES = [
    ("active", "Active"),
    ("graduated", "Graduated"),
    ("suspended", "Suspended"),
    ("withdrawn", "Withdrawn"),
]


class StudentForm(FlaskForm):
    student_number = StringField("Student Number", validators=[DataRequired(), Length(max=24)])
    first_name = StringField("First Name", validators=[DataRequired(), Length(max=80)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(max=80)])
    email = StringField("Email", validators=[Optional(), Email(), Length(max=255)])
    phone = StringField("Phone", validators=[Optional(), Length(max=32)])
    address = StringField("Address", validators=[Optional(), Length(max=255)])
    date_of_birth = DateField("Date of Birth", validators=[Optional()])
    department_id = SelectField("Department", coerce=int, validators=[Optional()], choices=[])
    program_id = SelectField("Program", coerce=int, validators=[Optional()], choices=[])
    admission_date = DateField("Admission Date", validators=[Optional()])
    enrollment_status = SelectField("Status", choices=STATUS_CHOICES, default="active")
    submit = SubmitField("Save Student")
