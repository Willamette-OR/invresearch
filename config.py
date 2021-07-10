import os


basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """This class defines configuration variables for the app."""

    SECRET_KEY = os.environ.get('SECRET_KEY') or \
        'this-is-hard-to-guess-so-do-not-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
