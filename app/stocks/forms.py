from flask_wtf import FlaskForm
from flask_ckeditor import CKEditorField
from wtforms import SubmitField, StringField
from wtforms.validators import DataRequired


class NoteForm(FlaskForm):
    """
    This class implements a form for users to take rich text notes on stocks.
    """

    body = CKEditorField('New Notes', validators=[DataRequired()])
    submit = SubmitField('Submit')


class CompareForm(FlaskForm):
    """
    This class implements a form for submitting multiple stock symbols for 
    comparison purposes.
    """

    symbols = StringField('Symbols', validators=[DataRequired()])
    submit = SubmitField('Compare')
