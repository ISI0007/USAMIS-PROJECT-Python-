"""WTForms for the authentication blueprint."""
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, Regexp


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(max=64)])
    password = PasswordField("Password", validators=[DataRequired(), Length(max=128)])
    submit = SubmitField("Sign In")


class RegistrationForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=160)])
    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(min=3, max=64, message="Use 3-64 characters."),
            Regexp(r"^[A-Za-z0-9._-]+$",
                   message="Letters, digits, dot, underscore and hyphen only."),
        ],
    )
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=8, message="Use at least 8 characters.")],
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    photo = FileField(
        "Profile photo",
        validators=[Optional(), FileAllowed(["png", "jpg", "jpeg", "gif", "webp"],
                                            "Images only (png, jpg, gif, webp).")],
    )
    submit = SubmitField("Create Account")


class ProfileForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=160)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    photo = FileField(
        "Profile photo",
        validators=[Optional(), FileAllowed(["png", "jpg", "jpeg", "gif", "webp"],
                                            "Images only (png, jpg, gif, webp).")],
    )
    submit = SubmitField("Save Changes")


class PasswordChangeForm(FlaskForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField(
        "New Password",
        validators=[DataRequired(), Length(min=8, message="Use at least 8 characters.")],
    )
    confirm_password = PasswordField(
        "Confirm New Password",
        validators=[DataRequired(), EqualTo("new_password", message="Passwords must match.")],
    )
    submit = SubmitField("Update Password")
