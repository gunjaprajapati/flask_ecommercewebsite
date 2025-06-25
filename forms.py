from flask_wtf import FlaskForm
from wtforms import TextAreaField, IntegerField, SubmitField
from wtforms.validators import DataRequired, NumberRange

class ReviewForm(FlaskForm):
    stars = IntegerField('Rating (1-5)', validators=[DataRequired(), NumberRange(min=1, max=5)])
    content = TextAreaField('Your Review', validators=[DataRequired()])
    submit = SubmitField('Submit')
