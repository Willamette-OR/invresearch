from os import times
import unittest
from datetime import datetime, timedelta
from app import app, db
from app.models import User, Post


class UserTestCase(unittest.TestCase):
    """
    This class implements unit tests for features of the User model, derived
    from unittest.TestCase
    """

    def setUp(self):
        """This method defines instructions to be executed before each test."""

        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        db.create_all()

    def tearDown(self):
        """This method defines instructions to be executed after each test."""

        db.session.remove()
        db.drop_all()

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
        




if __name__ == '__main__':
    unittest.main(verbosity=2)