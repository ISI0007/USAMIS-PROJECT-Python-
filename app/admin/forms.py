"""Admin forms."""
from flask_wtf import FlaskForm
from wtforms import PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional


class UserForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(max=64)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=160)])
    role = SelectField("Role", validators=[DataRequired()], choices=[])
    status = SelectField("Status", choices=[("active", "Active"), ("inactive", "Inactive"),
                                            ("blocked", "Blocked")], default="active")
    # Required on create; optional on edit (blank = keep current password).
    password = PasswordField("Password", validators=[Optional(), Length(min=8)])
    submit = SubmitField("Save User")
