import os

class Config:
    """This class defines configuration variables for the app."""

    SECRET_KEY = os.environ.get('SECRET_KEY') or 'this-is-hard-to-guess-so-do-not-guess'
