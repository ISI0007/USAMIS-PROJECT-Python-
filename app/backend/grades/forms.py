"""Grade forms."""
from flask_wtf import FlaskForm
from wtforms import BooleanField, DecimalField, HiddenField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, NumberRange, Optional


class GradeForm(FlaskForm):
    enrollment_id = HiddenField(validators=[DataRequired()])
    score = DecimalField("Score (0-100)", places=2,
                         validators=[DataRequired(), NumberRange(min=0, max=100)])
    remarks = TextAreaField("Remarks", validators=[Optional()])
    publish = BooleanField("Publish immediately")
    submit = SubmitField("Save Grade")
