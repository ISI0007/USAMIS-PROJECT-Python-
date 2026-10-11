"""Course forms."""
from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class CourseForm(FlaskForm):
    code = StringField("Course Code", validators=[DataRequired(), Length(max=16)])
    title = StringField("Title", validators=[DataRequired(), Length(max=160)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=2000)])
    credits = IntegerField("Credits", validators=[DataRequired(), NumberRange(min=1, max=12)],
                           default=3)
    department_id = SelectField("Department", coerce=int, validators=[Optional()], choices=[])
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save Course")
