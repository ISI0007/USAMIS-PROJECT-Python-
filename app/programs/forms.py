"""Program forms."""
from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class ProgramForm(FlaskForm):
    code = StringField("Code", validators=[DataRequired(), Length(max=16)])
    name = StringField("Name", validators=[DataRequired(), Length(max=160)])
    department_id = SelectField("Department", coerce=int, validators=[DataRequired()], choices=[])
    duration_years = IntegerField("Duration (years)",
                                  validators=[DataRequired(), NumberRange(min=1, max=8)], default=4)
    total_credits_required = IntegerField("Total Credits Required",
                                          validators=[DataRequired(), NumberRange(min=1, max=400)],
                                          default=120)
    description = TextAreaField("Description", validators=[Optional(), Length(max=1000)])
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save Program")
