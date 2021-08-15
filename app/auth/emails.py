from flask import render_template
from app import app
from app.emails import send_email


def send_password_reset_email(user):
    """This function sends a password reset email for the given user."""

    token = user.get_password_reset_token()
    send_email(subject='[InvResearch] Password Reset',
               sender=app.config['ADMINS'][0],
               recipients=[user.email],
               text_body=render_template('email/reset_password.txt', 
                                         user=user, token=token),
               html_body=render_template('email/reset_password.html',
                                         user=user, token=token))
