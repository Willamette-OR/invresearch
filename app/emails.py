from flask_mail import Message
from app import mail


def send_mail(subject, sender, recipients, text_body, html_body):
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
