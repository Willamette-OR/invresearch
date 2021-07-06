from flask import render_template
from app import app
from app.forms import LoginForm


@app.route('/')
@app.route('/index')
def index():
    """This function implements the view logic for the index page."""

    username = 'baiber'
    posts = [
        {'body': 'This is the first post!',
         'author': 'baiber'},
        {'body': 'This web app is about investment research!',
         'author': 'peipei'}
    ]

    return render_template('index.html', title='Home', username=username, posts=posts)


@app.route('/login')
def login():
    """This function implements the view logic for the login page."""

    form = LoginForm()

    return render_template('login.html', title='Login', form=form)
