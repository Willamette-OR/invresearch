from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from logging.handlers import SMTPHandler, RotatingFileHandler
import logging
import os
from config import Config


# initialize flask extentions as global variables so that they can be accessed 
# from anywhere
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
mail = Mail()
bootstrap = Bootstrap()
moment = Moment()


def create_app(config=Config):
    """This function creates a Flask app with a given config class."""

    app = Flask(__name__)
    app.config.from_object(config)

    # initialize flask extensions with the created app
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)
    bootstrap.init_app(app)
    moment.init_app(app)

    # incorporate the auth blueprint
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # incorporate the errors blueprint
    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    # incorporate the main blueprint
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    # set up logging when the created app is not in debug or testing mode
    if not app.debug and not app.testing:
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

        # log more running info to files
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/invresearch.log', maxBytes=10240,
                                        backupCount=10)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        app.logger.addHandler(file_handler)

        # configure app logger
        app.logger.setLevel(logging.INFO)
        app.logger.info('Invresearch startup')
    
    return app


from app import models
