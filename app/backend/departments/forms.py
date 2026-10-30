"""Department forms."""
from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class DepartmentForm(FlaskForm):
    code = StringField("Code", validators=[DataRequired(), Length(max=16)])
    name = StringField("Name", validators=[DataRequired(), Length(max=160)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=1000)])
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save Department")
