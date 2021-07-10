from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app import db 


class User(db.Model):
    """
    This class implements a table for storing data related to app users, 
    derived from SQLAlchemy's Model class.
    """

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    email = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    posts = db.relationship('Post', backref='author', lazy='dynamic')

    def __repr__(self):
        """This function defines the string repr of user objects."""

        return "<User: {}>".format(self.username)

    def set_password(self, password):
        """
        This function hashes the input password and saves the hash with the user.
        """

        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """This function checks the input password and returns True or False."""

        return check_password_hash(self.password_hash, password)


class Post(db.Model):
    """
    This class implements a table for storing post data for app users,
    derived from SQLAlchemy's Model class.
    """

    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        """This function defines the string repr of post objects."""

        return "<Post: {}>".format(self.body)
