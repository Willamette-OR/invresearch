import unittest
import numpy as np
from datetime import datetime, timedelta
from config import Config
from app import create_app, db
from app.models import User, Post, Message, Stock, StockNote
from app.metrics import Metric, TotalMetric


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

        # TODO - there are problems with this test.
        pass

        #user = User(username='john', email='john@example.com')
        #self.assertEqual(user.avatar(64), 
        #    'https://www.gravatar.com/avatar/'
        #    'd4c74594d841139328695756648b6bd6?d=identicon&s=64')

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
        self.assertEqual(revenue.percentile_rank(150), 0)
        self.assertEqual(revenue.percentile_rank(250), 50)
        
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

    def test_metric_valid_values(self):
        """
        This method tests the logic to get valid values for metrics.
        """

        # set up a test case
        name = 'revenue'
        timestamps = ['2016-09', '2017-09', '2018-09', '2019-09', '2020-09', 
                      '2021-09', 'TTM']
        values = [1, 2, -1, 4, 0, 5, 6]
        start_date = datetime(1900, 1, 1)
        revenue = Metric(name, timestamps, values, start_date)

        # test scenario 1
        valid_values = list(
            revenue.get_valid_values(num_of_years=4, 
                                     disregarded_values=[0, np.nan]))
        self.assertListEqual(valid_values, [-1, 4, 5])

        # test scenario 2
        valid_values = list(
            revenue.get_valid_values(num_of_years=4, 
                                     disregarded_values=[np.nan]))
        self.assertListEqual(valid_values, [-1, 4, 0, 5])

    def test_metric_percentile_rank(self):
        """
        This method tests the metric percentile rank logic.
        """

        name = 'revenue'
        timestamps = ['2017-01', '2018-01', '2019-01', '2020-01', '2021-01', 
                      'TTM']
        values = [1, -2, 0, 4, 5, 3]
        start_date = datetime(1900, 1, 1)
        revenue = Metric(name, timestamps, values, start_date)

        # scenario 1
        r = revenue.percentile_rank(target_value=values[-1])
        self.assertAlmostEqual(r, 50)

    def test_metric_pctrank_latest(self):
        """
        This method tests the logic for the latest metric value.
        """

        # set up a test case
        name = 'revenue'
        timestamps = ['2016-09', '2017-09', '2018-09', '2019-09', '2020-09', 
                      '2021-09', 'TTM']
        values = [1, 2, -1, 4, 0, 5, 4.5]
        start_date = datetime(1900, 1, 1)
        revenue = Metric(name, timestamps, values, start_date)

        # test scenario 1
        pctrank_latest_value = revenue.pctrank_of_latest(num_of_years=3)
        self.assertTupleEqual(pctrank_latest_value, (0.5, 4.5))

        # test scenario 2
        pctrank_latest_value = revenue.pctrank_of_latest(num_of_years=10)
        self.assertTupleEqual(pctrank_latest_value, (0.8, 4.5))

        # test scenario 3
        pctrank_latest_value = revenue.pctrank_of_latest(latest='')
        self.assertTupleEqual(pctrank_latest_value, (0.8, 5))

    def test_metric_growth_rate(self):
        """
        This method tests the metric growth rate calculations.
        """

        # set up a test case
        name = 'revenue'
        timestamps = ['2016-01', '2017-01', '2018-01', '2019-01', '2020-01', 
                      '2021-01', 'TTM']
        start_date = datetime(1900, 1, 1)

        # test scenario 1
        values = [3, 4, 3, 2, 2, 6, 5]
        revenue = Metric(name, timestamps, values, start_date)
        self.assertAlmostEqual(revenue.growth_rate(3, True), 0.231144413)
        self.assertAlmostEqual(revenue.growth_rate(5, True), 0.028420050)
        self.assertAlmostEqual(revenue.growth_rate(3, False), 0.9)

        # test scenario 2
        values = [3, 4, 3, -1, -3, 6, 5]
        revenue = Metric(name, timestamps, values, start_date)
        self.assertAlmostEqual(revenue.growth_rate(3, True), 0.259921050)
        self.assertAlmostEqual(revenue.growth_rate(3, False), 0.7)

        # test scenario 3
        values = [3, 4, -3, -1, -3, -6, 5]
        revenue = Metric(name, timestamps, values, start_date)
        self.assertAlmostEqual(revenue.growth_rate(3, True), None)
        self.assertAlmostEqual(revenue.growth_rate(3, False), -1.1)
        self.assertAlmostEqual(revenue.growth_rate(5, True), None)
        self.assertAlmostEqual(revenue.growth_rate(5, False), -1.828571429)

    def test_metric_rating(self):
        """
        This method tests the metric rating logic.
        """

        name = 'revenue'
        timestamps = ['2017-01', '2018-01', '2019-01', '2020-01', '2021-01', 
                      'TTM']
        values = [1, 2, 3, 4, 5, 6]
        start_date = datetime(1900, 1, 1)
        revenue = Metric(name, timestamps, values, start_date)

        # scenario 1
        rating_data = revenue.rating(
            benchmark_value=None, reverse=False, latest='TTM', debug=True)
        self.assertAlmostEqual(rating_data['rating'], 1)
        self.assertAlmostEqual(rating_data['rating_per_percentile_rank'], 1)
        self.assertAlmostEqual(rating_data['rating_per_trend_values'], 1)
        self.assertAlmostEqual(rating_data['rating_per_benchmark_value'], 0)
        
        # scenario 2
        rating_data = revenue.rating(
            benchmark_value=7, reverse=True, latest='latest', debug=True)
        self.assertAlmostEqual(rating_data['rating'], (0.2 / 3) + 1/3)
        self.assertAlmostEqual(rating_data['rating_per_percentile_rank'], 0.2)
        self.assertAlmostEqual(rating_data['rating_per_trend_values'], 0)
        self.assertAlmostEqual(rating_data['rating_per_benchmark_value'], 1)

        # scenario 3
        values = [1, -2, 0, 4, 5, 3]
        revenue = Metric(name, timestamps, values, start_date)
        rating_data = revenue.rating(
            benchmark_value=2, reverse=True, latest='TTM', debug=True)
        self.assertAlmostEqual(rating_data['rating'], 0.5/3)
        self.assertAlmostEqual(rating_data['rating_per_percentile_rank'], 0.5)
        self.assertAlmostEqual(rating_data['rating_per_trend_values'], 0)
        self.assertAlmostEqual(rating_data['rating_per_benchmark_value'], 0)

    def test_metric_range_stats(self):
        """
        This method tests the range stats calculations of metrics.
        """

        # set up a test case
        name = 'revenue'
        timestamps = ['2016-01', '2017-01', '2018-01', '2019-01', '2020-01', 
                      '2021-01', 'TTM']
        values = [3, 4, 1, 2, 0, 6, 5]
        start_date = datetime(1900, 1, 1)
        revenue = Metric(name, timestamps, values, start_date)

        # test different range stats
        revenue.min_4y, revenue.max_4y, revenue.median_4y, \
            revenue.pctrank_of_latest_4y = \
            revenue.get_range_info(number_of_years=4)
        self.assertEqual(revenue.min_4y, 1)
        self.assertEqual(revenue.max_4y, 6)
        self.assertEqual(revenue.median_4y, 2)
        self.assertAlmostEqual(revenue.pctrank_of_latest_4y[0], 2/3)

    def test_growth_metric_creation(self):
        """
        This method tests the logic to create 'growth' metrics from base 
        metrics.
        """

        # set up a test case
        name = 'revenue'
        timestamps = ['2016-01', '2017-01', '2018-01', '2019-01', '2020-01', 
                      '2021-01', 'TTM']
        values = [3, 4, 1, 2, 0, 6, 5]
        start_date = datetime(1900, 1, 1)
        revenue = Metric(name, timestamps, values, start_date)

        # test case 1
        revenue_3ygrowth = revenue.get_growth_metric()
        self.assertEqual(len(revenue_3ygrowth.values), len(revenue.values))
        self.assertAlmostEqual(revenue_3ygrowth.values[-1], 0.817120593)
        self.assertAlmostEqual(revenue_3ygrowth.values[-2], 0)
        self.assertAlmostEqual(revenue_3ygrowth.values[-3], -0.229155775)
        self.assertAlmostEqual(revenue_3ygrowth.values[0], 0)

    def test_stock_notes(self):
        """
        This method tests the database mechanics of stock notes.
        """

        # set up
        user = User(username='bob')
        stock = Stock(symbol='APPL')
        note = StockNote(body='foo', user=user, stock=stock)
        db.session.add_all([user, stock, note])
        db.session.commit()

        # test case 1
        first_note = StockNote.query.filter_by(user=user).first()
        self.assertEqual(first_note.id, note.id)
        self.assertEqual(first_note.stock_id, stock.id)
        self.assertEqual(first_note.body, 'foo')
        note_1 = user.stock_notes.first()
        note_2 = stock.stock_notes.first()
        self.assertEqual(note_1.id, note_2.id)

    def test_post_replies(self):
        """
        This method tests the database logic for post replies.
        """

        # set up
        user = User(username='alice')
        db.session.add(user)
        db.session.commit()

        # basic reply querying
        post = Post(body='parent', author=user)
        self.assertIsNone(post.parent)
        child_1 = Post(body='child 1', author=user, parent=post)
        child_2 = Post(body='child 2', author=user, parent=post)
        self.assertListEqual(post.children.all(), [child_1, child_2])
        self.assertEqual(child_1.parent, post)
        grandchild_11 = Post(body='grandchild 1-1', author=user, parent=child_1)
        self.assertListEqual(child_1.children.all(), [grandchild_11])
        self.assertEqual(grandchild_11.parent, child_1)

        # query ordered replies
        post = Post(body='another parent', author=user)
        db.session.add(post)
        db.session.commit()
        now = datetime.utcnow()
        second = Post(
            body='second', author=user, parent=post, 
            timestamp=now + timedelta(3))
        third = Post(
            body='third', author=user, parent=post, 
            timestamp=now + timedelta(10))
        first = Post(
            body='first', author=user, parent=post, 
            timestamp=now)
        self.assertListEqual(post.get_replies().all(), [third, second, first])

if __name__ == '__main__':
    unittest.main(verbosity=2)
