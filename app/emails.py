from flask import render_template
from flask_mail import Message
from app import app, mail


def send_email(subject, sender, recipients, text_body, html_body):
    """
    This function configures and sends out messages via app-configured email 
    settings.
    """

    msg = Message(subject=subject, 
                  sender=sender,
                  recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    mail.send(msg)


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
