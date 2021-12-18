from datetime import date, datetime
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
from app.stocksdata import get_quote, get_quote_history, \
                           get_financials_history, get_analyst_estimates, \
                           get_quote_details
from app.fundamental_analysis import get_fundamental_indicators


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


# auxiliary table for the many-to-many relationship for user following
followers = db.Table(
    'followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
    )


# auxiliary table for the many-to-many relationship for stock watching
watchers = db.Table(
    'watchers',
    db.Column('watcher_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('watched_id', db.Integer, db.ForeignKey('stock.id'))
)


class Stock(db.Model):
    """
    This class implements a data model for storing & operating on asset data, 
    derived from the parent class of db.Model.
    """

    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(16), unique=True, index=True)
    name = db.Column(db.String(128))
    last_quote_update = db.Column(db.Float, index=True, default=None)
    quote_payload = db.Column(db.Text)
    last_financials_history_update = db.Column(db.DateTime, index=True, 
                                               default=None)
    financials_history_payload = db.Column(db.Text)
    last_quote_history_update = db.Column(db.DateTime, index=True, 
                                          default=None)
    analyst_estimates_payload = db.Column(db.Text)
    last_analyst_estimates_update = db.Column(db.DateTime, index=True, 
                                              default=None)
    quote_history_payload = db.Column(db.Text)
    quote_details_paylod = db.Column(db.Text)
    last_quote_details_update = db.Column(db.DateTime, index=True, default=None)
    dividend_yield = db.Column(db.Float, index=True)

    def __repr__(self):
        return "<Stock: {}>".format(self.symbol)

    def update_quote(self, delay=60):
        """
        This method gets the latest quote for the current stock.

        Input:
            - delay: number of seconds within which the quote will not be
                     updated even when the method is called. The default
                     value is 60.
        """

        # only update the quote if it's been more than the number of 'delay' 
        # seconds since the last update
        now = time()
        if not self.last_quote_update or \
            (now - self.last_quote_update) > delay:
            self.quote_payload = json.dumps(get_quote(self.symbol))
            self.last_quote_update = time()

    def get_financials_history_data(self, update_interval_days=30):
        """
        This method gets the historical data of stock financials in the app 
        database, and fetches for newer data if the time lapse since the last 
        update has already exceeded the given update interval (in days).
        """

        # update the financials history payload column if the last update
        # timestamp is None (never initialized/updated before), or if the time 
        # lapse has exceeded the present update internal
        last_update_time = self.last_financials_history_update or \
            datetime(1900, 1, 1)
        now = datetime.utcnow()
        lapse_days = (now - last_update_time).days
        if lapse_days > update_interval_days:
            self.financials_history_payload = \
                json.dumps(get_financials_history(self.symbol))
            self.last_financials_history_update = now
            db.session.commit()

        return json.loads(self.financials_history_payload)
    
    def get_analyst_estimates_data(self, update_interval_days=30):
        """
        This method returns the analyst estimates data in a dictionary.

        Before that, it first fetches for and saves newer data if the # of 
        days since the last update has exceeded a preset threshold 
        (update_interval_days).
        """

        # fetches for newer data if update is needed
        now = datetime.utcnow()
        if not self.last_analyst_estimates_update or (now - \
            self.last_analyst_estimates_update).days > update_interval_days:
            self.analyst_estimates_payload = json.dumps(
                get_analyst_estimates(self.symbol))
            self.last_analyst_estimates_update = now
            db.session.commit()

        return json.loads(self.analyst_estimates_payload)

    def get_quote_history_data(self, start_date, end_date, 
                               interval='1mo', type='close', delay=24):
        """
        This method creates/refreshes the quote history payload if needed,
        and returns the quote history data in a dictionary of:
            "<timestamp>: <price>"

        Inputs:
            'start_date': '%m-%d-%Y'. 
            'end_date': '%m-%d-%Y'. 
            'type': the type of stock price. Default is 'close' (closing price)
            'delay': the minimal number of hours allowed between two refreshes;
                     Default is 24 hours.
        """

        # creates/refreshes the quote history and save it 
        now = datetime.utcnow()
        if not self.last_quote_history_update or \
            (now - self.last_quote_history_update).total_seconds() > \
                (delay * 3600):

            # download quote history from the web
            raw_data = get_quote_history(symbol=self.symbol, 
                                         interval=interval,
                                         header=type)
            
            # convert all timestamp values to strings and save
            raw_data_timestamp_to_str = {key.strftime('%m-%d-%Y %H:%M'): value \
                                         for (key, value) in raw_data.items()}
            self.quote_history_payload = json.dumps(raw_data_timestamp_to_str)

            # update the saved timestamp for the last quote history update
            self.last_quote_history_update = now

            # commit database changes 
            db.session.commit()

        # load quote data from the saved quote history payload, with 
        # pre-specified start and end dates
        raw_data = {datetime.strptime(key, '%m-%d-%Y %H:%M'): value for \
            (key, value) in json.loads(self.quote_history_payload).items()}
        timestamp_start_date = datetime.strptime(start_date, '%m-%d-%Y')
        timestamp_end_date = datetime.strptime(end_date, '%m-%d-%Y')
        return {key: value for (key, value) in raw_data.items() \
                if timestamp_start_date <= key <= timestamp_end_date}

    def get_quote_details_data(self, delay_hours=24):
        """
        This method creates/refreshes a saved quote details payload if needed, 
        and returns the data in a dictionary such as <'Beta': 1.0>

        Inputs:
            'delay_days': number of hours to wait before downloading new quote 
                          details data from the web. 
                          Defaulted to 24.
        """

        now = datetime.utcnow()
        if not self.last_quote_details_update or \
            (now - self.last_quote_details_update).total_seconds() >= \
                delay_hours * 3600:
            data, self.dividend_yield = get_quote_details(self.symbol)
            self.quote_details_paylod = json.dumps(data)
            self.last_quote_details_update = now
            db.session.commit()

        return json.loads(self.quote_details_paylod)

    def get_fundamental_indicator_data(self, start_date='01-01-1900'):
        """
        This method gets/calculates fundamental indicators from the saved 
        financials history payload, and returns them in a nested dictionary 
        including different categories of indicators, such as 'Financial 
        Strength', 'Growth', etc.

        Inputs:
            'start_date': a Python datetime object. 
                          Only data of financials history after this date will 
                          be used when deriving fundamental indicators.
                          Defaulted to be 1/1/1900.
        """
        
        return get_fundamental_indicators(
            financials_history=self.get_financials_history_data(), 
            start_date=datetime.strptime(start_date, '%m-%d-%Y')
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
    watched = db.relationship('Stock', secondary=watchers, 
                              primaryjoin=(id==watchers.c.watcher_id),
                              secondaryjoin=(Stock.id==watchers.c.watched_id),
                              backref=db.backref('watchers', lazy='dynamic'),
                              lazy='dynamic')

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

    def is_watching(self, stock):
        """
        This method checks if the current user is already watching the given stock.
        """

        return self.watched.filter(watchers.c.watched_id==stock.id).count() > 0

    def watch(self, stock):
        """
        This method gets the current user to watch the given stock, if the 
        current user is not already watching the stock.
        """

        if not self.is_watching(stock):
            self.watched.append(stock)

    def unwatch(self, stock):
        """
        This method gets the current user to unwatch the given stock, if the 
        current user is already watching the stock.
        """

        if self.is_watching(stock):
            self.watched.remove(stock)

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
