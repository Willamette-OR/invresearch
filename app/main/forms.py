import os
import imghdr
from flask import request, current_app
from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, ValidationError, Length
from app.models import User


class EditProfileForm(FlaskForm):
    """This class defines the profile editing form, derived from FlaskForm."""

    username = StringField('Username', validators=[DataRequired()])
    avatar = FileField('Profile Photo')
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

    def validate_avatar(self, avatar):
        """
        This method validates if the uploaded file:
            1. has a proper file extension;
            2. is not too large;
            3. has a byte content consistent with the given file extension
        """

        # validate the file extension
        file_ext = os.path.splitext(avatar.data.filename)[1].lower()
        if file_ext not in current_app.config['UPLOAD_EXTENSIONS']:
            raise ValidationError(
                "Invalid file type. Only these files are accepted: " + 
                ", ".join(current_app.config['UPLOAD_EXTENSIONS']))

        # validate the file size
        file_size = len(avatar.data.read())
        avatar.data.seek(0)
        if file_size >= current_app.config['MAX_UPLOAD_SIZE']:
            raise ValidationError(
                "The uploaded file has to be less than: {:.1f} MB.".format(
                    current_app.config['MAX_UPLOAD_SIZE'] / 1024**2))

        # validate the file content
        file_header = avatar.data.read(500)
        avatar.data.seek(0)
        file_format = imghdr.what(None, file_header)
        if file_format is None:
            detected_ext = None
        else:
            detected_ext = \
                "." + (file_format if file_format != 'jpeg' else 'jpg')
        if detected_ext != file_ext:
            raise ValidationError("The detected file content ({}) does not "
            "match the file extension ({}).".format(detected_ext, file_ext))


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
    parent_id = StringField()
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
