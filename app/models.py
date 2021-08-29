from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app
from flask_login import UserMixin
from hashlib import md5
from time import time
import jwt
import json
import rq
import redis
from app import db, login 
from app.search import query_index, add_to_index, remove_from_index


class SearchableMixin(object):
    """This class implements search related methods for data models."""

    @classmethod
    def search(cls, expression, page, per_page):
        """This class method does the search through the current data model."""

        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        
        # return a null table if nothing was found through the search
        if total == 0:
            return cls.query.filter_by(id=0), total

        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))

        return cls.query.filter(cls.id.in_(ids)).order_by(
            db.case(when, value=cls.id)), total

    @classmethod
    def before_commit(cls, session):
        """
        This class method saves the session info for updating the search index 
        later.
        """

        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
            }

    @classmethod
    def after_commit(cls, session):
        """
        This class method updates the search index with session changes just committed.
        """

        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)

        # reset the attribute after updating the search index
        session._changes = None

    @classmethod
    def reindex(cls):
        """This method reindexes all instances of the data model."""

        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)


# register SearchableMixin methods with the database session
db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)


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
    sent_messages = db.relationship('Message', 
                                    foreign_keys='Message.sender_id', 
                                    backref='author', lazy='dynamic')
    received_messages = db.relationship('Message', 
                                        foreign_keys='Message.recipient_id', 
                                        backref='recipient', lazy='dynamic')
    last_message_read_time = db.Column(db.DateTime)
    notifications = db.relationship('Notification', backref='user', 
                                    lazy='dynamic')
    tasks = db.relationship('Task', backref='user', lazy='dynamic')

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

    def followed_posts(self):
        """
        This method queries the object's own posts and all followed users' 
        posts.
        """

        followed = Post.query.join(
            followers, (Post.user_id==followers.c.followed_id)).filter(
            self.id==followers.c.follower_id)
        own = Post.query.filter_by(user_id=self.id)
        return followed.union(own).order_by(Post.timestamp.desc())

    def get_password_reset_token(self, expires_in=600):
        """
        This method generates a password reset token that expires after a 
        given time window.
        """

        return jwt.encode(
            {'reset_password': self.id, 'exp': (time() + expires_in)}, 
            key=current_app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def verify_password_reset_token(token):
        """
        This method verifies a password reset token, and if verified returns 
        a user object for password reset.
        """

        try:
            id = jwt.decode(token, key=current_app.config['SECRET_KEY'], 
                                 algorithms='HS256')['reset_password']
        except:
            return 
        else:
            return User.query.get(id)

    def new_messages(self):
        """This method returns the number of new messages."""

        last_read_time = self.last_message_read_time or datetime(1900, 1, 1)
        return Message.query.filter_by(recipient=self).filter(
            Message.timestamp > last_read_time).count()

    def add_notification(self, name, data):
        """
        This method updates user notifications with a given name for the 
        notification, as well as the data included for the notification.
        """

        # first delete notifications of the same name if any
        self.notifications.filter_by(name=name).delete()

        n = Notification(name=name, user=self, payload_json=json.dumps(data))
        db.session.add(n)

        return n

    def launch_task(self, name, description, *args, **kwargs):
        """
        This method launches a new task via the task queue configured for the 
        app, and logs related info to the Task database.
        """

        rq_job = current_app.task_queue.enqueue('app.tasks.' + name, self.id, 
                                                *args, **kwargs)
        task = Task(id=rq_job.get_id(), name=name, description=description, 
                    user=self)
        db.session.add(task)

        return task

    def get_tasks_in_progress(self):
        """This method returns all tasks in progress."""

        return self.tasks.filter_by(complete=False).all()

    def get_task_in_progress(self, name):
        """
        This method returns the task of the given name that is still in 
        progress.
        """

        return self.tasks.filter_by(name=name, complete=False).first()


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class Post(SearchableMixin, db.Model):
    """
    This class implements a table for storing post data for app users,
    derived from SQLAlchemy's Model class.
    """

    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    language = db.Column(db.String(5))

    # fields available for search
    __searchable__ = ['body']

    def __repr__(self):
        """This function defines the string repr of post objects."""

        return "<Post: {}>".format(self.body)


class Message(db.Model):
    """
    This class implements a data model for storing user messages, drived from 
    the parent class db.Model.
    """

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    body = db.Column(db.String(140))

    def __repr__(self):
        return "<Message: {}>".format(self.body)


class Notification(db.Model):
    """
    This class implements a data model for storing user notifications, derived 
    from the parent class db.Model.
    """

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(128), index=True)
    timestamp = db.Column(db.Float, index=True, default=time)
    payload_json = db.Column(db.Text)

    def get_data(self):
        """
        This method deserializes data stored in the payload column and returns 
        it as a string.
        """

        return json.loads(str(self.payload_json))


class Task(db.Model):
    """
    This class implements a data model for storing user tasks, derived from 
    the parent class db.Model.
    """

    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    complete = db.Column(db.Boolean, default=False)

    def get_rq_job(self):
        """
        This method retrieves the job associated with the current task.
        If the Redis connection is unavailable or there is no such job sharing 
        the given task id, return None.
        """

        try:
            rq_job = rq.job.Job.fetch(self.id, connection=current_app.redis)
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return None
        return rq_job


    def get_progress(self):
        """
        This method retrieves the progress of the job associated with the 
        current task.
        """

        job = self.get_rq_job()
        return job.meta.get('progress', 0) if job is not None else 100
