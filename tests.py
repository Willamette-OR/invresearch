import unittest
from datetime import datetime, timedelta
from config import Config
from app import create_app, db
from app.models import User, Post, Message, Stock
from app.stocks.metrics import Metric, TotalMetric


class TestingConfig(Config):
    """
    This class implements a testing configuration class, derived from the 
    parent class Config.
    """

    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'


class UserTestCase(unittest.TestCase):
    """
    This class implements unit tests for features of the User model, derived
    from unittest.TestCase
    """

    def setUp(self):
        """This method defines instructions to be executed before each test."""

        self.app = create_app(TestingConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        """This method defines instructions to be executed after each test."""

        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_password(self):
        """This method tests the password feature."""

        user = User(username='john')
        user.set_password('dog')
        self.assertTrue(user.check_password('dog'))
        self.assertFalse(user.check_password('cat'))

    def test_avatar(self):
        """This method tests the avatar feature."""

        user = User(username='john', email='john@example.com')
        self.assertEqual(user.avatar(64), 
            'https://www.gravatar.com/avatar/'
            'd4c74594d841139328695756648b6bd6?d=identicon&s=64')

    def test_follow(self):
        """This method tests the user following mechanics."""

        u1 = User(username='alice')
        u2 = User(username='bob')
        db.session.add_all([u1, u2])
        db.session.commit()

        self.assertFalse(u1.is_following(u2))
        self.assertFalse(u2.is_following(u1))
        self.assertEqual(u1.followed.count(), 0)
        self.assertEqual(u2.followers.count(), 0)

        u1.follow(u2)
        db.session.commit()

        self.assertTrue(u1.is_following(u2))
        self.assertEqual(u1.followed.count(), 1)
        self.assertEqual(u2.followers.count(), 1)

        u1.unfollow(u2)
        db.session.commit()

        self.assertFalse(u1.is_following(u2))
        self.assertEqual(u1.followed.count(), 0)
        self.assertEqual(u2.followers.count(), 0)

    def test_followed_posts(self):
        """This method tests the followed posts feature."""

        u1 = User(username='john')
        u2 = User(username='susan')
        u3 = User(username='alice')
        u4 = User(username='bob')
        db.session.add_all([u1, u2, u3, u4])

        now = datetime.utcnow()
        p1 = Post(body='post from john', author=u1, timestamp=(
            now + timedelta(seconds=3)))
        p2 = Post(body='post from susan', author=u2, timestamp=(
            now + timedelta(seconds=1)))
        p3 = Post(body='post from alice', author=u3, timestamp=(
            now + timedelta(seconds=9)))
        p4 = Post(body='post from bob', author=u4, timestamp=(
            now + timedelta(seconds=5)))
        db.session.add_all([p1, p2, p3, p4])
        db.session.commit()

        u1.follow(u2) # john follows susan
        u1.follow(u4) # john follows bob
        u2.follow(u1) # susan follows john
        u3.follow(u4) # alice follows bob
        u4.follow(u2) # bob follows susan
        u4.follow(u3) # bob follows alice
        db.session.commit()

        f1 = u1.followed_posts().all()
        f2 = u2.followed_posts().all()
        f3 = u3.followed_posts().all()
        f4 = u4.followed_posts().all()
        self.assertEqual(f1, [p4, p1, p2])
        self.assertEqual(f2, [p1, p2])
        self.assertEqual(f3, [p3, p4])
        self.assertEqual(f4, [p3, p4, p2])
        
    def test_password_reset_token(self):
        """This method test password reset token features."""

        user = User(username='bob', email='bob@example.com')
        db.session.add(user)
        db.session.commit()
        token = user.get_password_reset_token()
        self.assertTrue(token is not None)
        self.assertEqual(User.verify_password_reset_token(token), user)
        self.assertTrue(User.verify_password_reset_token(token+'foo') is None)

    def test_user_messages(self):
        u1 = User(username='alice')
        u2 = User(username='bob')
        db.session.add_all([u1, u2])
        db.session.commit()

        now = datetime.utcnow()
        m1 = Message(body='alice to bob', author=u1, recipient=u2, 
                     timestamp=now + timedelta(seconds=1))
        m2 = Message(body='bob to alice', author=u2, recipient=u1, 
                     timestamp=now + timedelta(seconds=4))
        m3 = Message(body='bob to alice again', author=u1, recipient=u2, 
                     timestamp=now + timedelta(seconds=2))             
        db.session.add_all([m1, m2, m3])
        db.session.commit()

        self.assertEqual(str(m1), "<Message: alice to bob>")
        self.assertEqual(u1.new_messages(), 1)
        self.assertEqual(u2.new_messages(), 2)
        u2.last_message_read_time = now + timedelta(seconds=10)
        self.assertEqual(u2.new_messages(), 0)

    def test_user_notifications(self):
        """This method test data modeling & methods related to notifications"""

        u = User(username='alice')
        db.session.add(u)
        db.session.commit()

        # add a first notification
        u.add_notification(name='message_count', data={'count': 3})
        db.session.commit()
        self.assertEqual(u.notifications.count(), 1)
        self.assertEqual(int(u.notifications.first().get_data()['count']), 3)

        # updates the first notification
        u.add_notification(name='message_count', data={'count': 5})
        db.session.commit()
        self.assertEqual(u.notifications.count(), 1)
        self.assertEqual(int(u.notifications.first().get_data()['count']), 5)

    def test_stock_watching(self):
        """This method tests the stock watching database mechanics."""

        u1 = User(username='alice')
        u2 = User(username='bob')
        s1 = Stock(symbol='AAPL')
        s2 = Stock(symbol='GOOGL')
        s3 = Stock(symbol='AMZN')
        db.session.add_all([u1, u2, s1, s2, s3])
        db.session.commit()

        # before users start watching any stocks
        self.assertEqual(str(s1), '<Stock: AAPL>')
        self.assertFalse(u1.is_watching(s1))
        self.assertFalse(u2.is_watching(s2))
        self.assertFalse(u2.is_watching(s3))

        # start several watchings
        u1.watch(s2)
        u1.watch(s3)
        u2.watch(s1)
        u2.watch(s3)
        db.session.commit()

        # re-check watching relationships
        self.assertFalse(u1.is_watching(s1))
        self.assertTrue(u1.is_watching(s2))
        self.assertEqual(u1.watched.count(), 2)
        self.assertFalse(u2.is_watching(s2))
        self.assertTrue(u2.is_watching(s3))
        self.assertEqual(u2.watched.count(), 2)
        self.assertEqual(s3.watchers.count(), 2)

        # check unwatching
        u2.unwatch(s3)
        db.session.commit()

        self.assertFalse(u2.is_watching(s3))
        self.assertEqual(u2.watched.count(), 1)
        self.assertEqual(s3.watchers.count(), 1)

    def test_metric_manipulations(self):
        """
        This method tests manipulations of metrics from financial reports.
        """

        # mock up inputs
        name = 'revenue'
        timestamps = ['2018-01', '2019-01', '2020-01', 'TTM']
        values = ['100', '200', '300', '350']
        start_date = datetime(2018, 5, 1)

        # test instance initialization
        revenue = Metric(name=name, timestamps=timestamps, values=values, 
                         start_date=start_date)
        self.assertEqual(revenue.name, name)
        self.assertEqual(revenue.timestamps, (datetime(2019, 1, 1), 
                                              datetime(2020, 1, 1)))
        self.assertEqual(revenue.values, (200, 300))
        self.assertEqual(revenue.TTM_value, 350)
        self.assertEqual(revenue.data, {datetime(2019, 1, 1): 200,
                                        datetime(2020, 1, 1): 300})
        
        # test operator overloading
        operating_income = Metric(name='operating income', 
                                  timestamps=timestamps, 
                                  values=['50', '100', '100', '175'], 
                                  start_date=start_date)
        rev_to_oi = revenue / operating_income
        self.assertEqual(rev_to_oi.name, 'revenue / operating income')
        self.assertEqual(rev_to_oi.timestamps, (datetime(2019, 1, 1), 
                                                datetime(2020, 1, 1)))
        self.assertEqual(rev_to_oi.values, (2.0, 3.0))
        self.assertEqual(rev_to_oi.TTM_value, 2.0)

        rev_plus_oi = revenue + operating_income
        self.assertEqual(rev_plus_oi.name, 'revenue + operating income')
        self.assertEqual(rev_plus_oi.timestamps, (datetime(2019, 1, 1), 
                                                  datetime(2020, 1, 1)))
        self.assertEqual(rev_plus_oi.values, (300, 400))
        self.assertEqual(rev_plus_oi.TTM_value, 525)

        # test per share operations
        num_of_shares = [100, 150]
        revenue = TotalMetric(name=name, timestamps=timestamps, values=values, 
                              start_date=start_date)
        revenue.num_of_shares = num_of_shares
        self.assertEqual(revenue.num_of_shares, num_of_shares)
        self.assertEqual(revenue.per_share_values, [2, 2])
        self.assertEqual(revenue.per_share_data, {datetime(2019, 1, 1): 2,
                                                  datetime(2020, 1, 1): 2})

        # test operations on analyst estimated data
        num_of_shares_estimated = [100]
        timestamps_estimated = ['202112', '202212', '202312']
        values_estimated = ['100', '200', '300']
        revenue_estimated = TotalMetric(name=name, 
                                        timestamps=timestamps_estimated, 
                                        values=values_estimated, 
                                        start_date=start_date,
                                        input_timestamps_format='%Y%m')
        revenue_estimated.num_of_shares = num_of_shares_estimated
        self.assertEqual(revenue_estimated.num_of_shares, [100, 100, 100])
        self.assertEqual(revenue_estimated.per_share_data, 
                         {datetime(2021, 12, 1): 1,
                          datetime(2022, 12, 1): 2,
                          datetime(2023, 12, 1): 3})


if __name__ == '__main__':
    unittest.main(verbosity=2)
