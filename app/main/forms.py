from flask import request, current_app
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileSize
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, ValidationError, Length
from app.models import User


class EditProfileForm(FlaskForm):
    """This class defines the profile editing form, derived from FlaskForm."""

    username = StringField('Username', validators=[DataRequired()])
    avatar = FileField('Profile Photo', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif']), FileSize(1024 * 1024)])
    about_me = TextAreaField('About Me', validators=[Length(min=1, max=140)])
    submit = SubmitField('Submit')

    def __init__(self, original_username, *args, **kwargs):
        """
        This constructor is overloaded in order to initialize the form instance 
        with an original username.
        """

        super().__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        """
        This method validates if the submitted username is already used by 
        someone else.
        """

        if username.data != self.original_username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError("Please use a different username.")


class EmptyForm(FlaskForm):
    """
    This class defines an empty form for requests that need protection from 
    CSRF, derived from FlaskForm.
    """

    submit = SubmitField('Submit')


class SubmitPostForm(FlaskForm):
    """
    This class implements a form for users to submit posts, derived from 
    FlaskForm.
    """

    post = TextAreaField(
        'Say something', validators=[DataRequired(), Length(min=1, max=140)])
    submit = SubmitField('Submit')


class SearchForm(FlaskForm):
    """This class implements a form for searching user posts."""

    q = StringField('Search', validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        """
        This constructor method changes the default values of a couple of args 
        needed for the search form.
        """

        if 'formdata' not in kwargs:
            kwargs['formdata'] = request.args
        if 'csrf_enabled' not in kwargs:
            kwargs['csrf_enabled'] = False
        super().__init__(*args, **kwargs)


class MessageForm(FlaskForm):
    """This class implements a form to send user messages."""

    body = TextAreaField('Message', validators=[DataRequired(), 
                         Length(min=1, max=140)])
    submit = SubmitField('Send')
