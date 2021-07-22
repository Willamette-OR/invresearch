from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import logging
from logging.handlers import SMTPHandler
from config import Config


app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login = LoginManager(app)
login.login_view = 'login'


if not app.debug:
    # only enable error reports via email when MAIL_SERVER is configured.
    if app.config['MAIL_SERVER']:
        host = (app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        auth = None
        if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
            auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        secure = None
        if app.config['MAIL_USE_TLS']:
            secure = ()
        mail_handler = SMTPHandler(mailhost=host, 
                                   fromaddr='no-reply@' + app.config['MAIL_SERVER'],
                                   toaddrs=app.config['ADMINS'],
                                   subject='InvResearch Failure',
                                   credentials=auth, secure=secure)
        mail_handler.setLevel(logging.ERROR)
        mail_handler.setFormatter(logging.Formatter(
            '[%(asctime)s] [%(levelname)s] in [%(module)s]: %(message)s'
        ))
        app.logger.addHandler(mail_handler)


from app import routes, models, errors
