from flask import current_app
from flask_mail import Message
from threading import Thread
from app import mail


def send_async_email(app, msg):
    """This helper function is used to send emails asynchronously."""

    with app.app_context():
        mail.send(msg)


def send_email(subject, sender, recipients, text_body, html_body, 
               attachments=None, sync=False):
    """
    This function configures and sends out messages via app-configured email 
    settings.
    """

    msg = Message(subject=subject, 
                  sender=sender,
                  recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    if attachments is not None:
        for attachment in attachments:
            msg.attach(*attachment)
    if sync:
        mail.send(msg)
    else:
        Thread(target=send_async_email, args=(
            current_app._get_current_object(), msg)).start()
