from flask_wtf import FlaskForm
from flask_ckeditor import CKEditorField
from wtforms import SubmitField
from wtforms.validators import DataRequired


class NoteForm(FlaskForm):
    """
    This class implements a form for users to take rich text notes on stocks.
    """

    body = CKEditorField('New Notes', validators=[DataRequired()])
    submit = SubmitField('Submit')
