from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField
from wtforms.validators import DataRequired


class NoteForm(FlaskForm):
    """
    This class implements a form for users to take rich text notes on stocks.
    """

    body = TextAreaField('New Notes', validators=[DataRequired()])
    submit = SubmitField('Submit')
