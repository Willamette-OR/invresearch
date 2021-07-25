from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from hashlib import md5
from app import db, login 


followers = db.Table(
    'followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
    )


class User(UserMixin, db.Model):
    """
    This class implements a table for storing data related to app users, 
    derived from SQLAlchemy's Model class.
    """

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    email = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    followed = db.relationship('User', secondary=followers, 
        primaryjoin=(id==followers.c.follower_id),
        secondaryjoin=(followers.c.followed_id==id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic'
        )

    def __repr__(self):
        """This method defines the string repr of user objects."""

        return "<User: {}>".format(self.username)

    def set_password(self, password):
        """
        This method hashes the input password and saves the hash with the user.
        """

        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """This method checks the input password and returns True or False."""

        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        """
        This method takes a given image size, hashes the user email address, 
        and returns a Gravatar url.
        """

        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
                digest, size)

    def is_following(self, user):
        """This method checks if the object is following a given user."""

        return self.followed.filter(
            followers.c.followed_id==user.id).count() > 0

    def follow(self, user):
        """This method adds the given user to the object's followed list."""

        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        """
        This method removes the given user from the object's followed list.
        """

        if self.is_following(user):
            self.followed.remove(user)


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


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
