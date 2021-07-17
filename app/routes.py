from flask import render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.urls import url_parse
from app import app, db
from app.forms import LoginForm, RegistrationForm
from app.models import User


@app.route('/')
@app.route('/index')
@login_required
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


@app.route('/login', methods=['GET', 'POST'])
def login():
    """This function implements the view logic for the login page."""

    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if not user or not user.check_password(form.password.data):
            flash("Incorrect username or password. Please try again.")
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        flash("You have logged in successfully!")
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            return redirect(url_for('index'))
        return redirect(next_page)
        
    return render_template('login.html', title='Login', form=form)


@app.route('/logout')
def logout():
    """This function implements the logic to log out users."""

    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """This function implements the view logic to register new users."""

    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("You have registered successfully!")
        return redirect(url_for('login'))

    return render_template('register.html', title='Register', form=form)
