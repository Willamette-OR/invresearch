from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError
from app.models import User


class LoginForm(FlaskForm):
    """This class is a child class of FlaskForm, which defines the login form for the app."""

    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')


class RegistrationForm(FlaskForm):
    """This class defines the user registration form, derived from FlaskForm."""

    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    repeat_password = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        """This method validates if the username already exists."""

        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError("Please use a different username.")

    def validate_email(self, email):
        """This method validates if the email address has already been registered."""

        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError("Please use a different email address.")
