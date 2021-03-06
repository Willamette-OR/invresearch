import os
from dotenv import load_dotenv


basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    """This class defines configuration variables for the app."""

    SECRET_KEY = os.environ.get('SECRET_KEY') or \
        'this-is-hard-to-guess-so-do-not-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['gongwei619@hotmail.com']
    POSTS_PER_PAGE = 10
    MS_TRANSLATOR_KEY = os.environ.get('MS_TRANSLATOR_KEY')
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://'
    FINNHUB_API_KEY = os.environ.get('FINNHUB_API_KEY')
    GURU_API_KEY = os.environ.get('GURU_API_KEY')
    STOCK_VALUATION_METRIC_DEFAULT = 'Revenue'
    EMAIL_LOGGING = os.environ.get('EMAIL_LOGGING') or False
    UPLOAD_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif']
    MAX_UPLOAD_SIZE = 1024 * 1024
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024
