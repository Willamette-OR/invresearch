from flask import render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.urls import url_parse
from datetime import datetime
from app import app, db
from app.forms import EditProfileForm, LoginForm, RegistrationForm, EmptyForm, \
    SubmitPostForm
from app.models import User, Post


@app.before_request
def before_request():
    """
    This function handles operations to perform before each request, 
    registered with the app.
    """

    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    """This function implements the view logic for the index page."""

    posts = current_user.followed_posts().all()
    form = SubmitPostForm()
    if form.validate_on_submit():
        post = Post(body=form.post.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash("Your new post is now live!")
        return redirect(url_for('index'))

    return render_template('index.html', title='Home', 
                           posts=posts, form=form)


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


@app.route('/user/<username>')
@login_required
def user(username):
    """This view function implements the logic to display user profiles."""

    user = User.query.filter_by(username=username).first_or_404()
    form = EmptyForm()
    
    return render_template('user.html', title='User Profile', user=user, 
                           form=form)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """This view function implements the logic to edit user profiles."""

    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash("Your profile has been updated successfully!")
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    
    return render_template('edit_profile.html', title='Edit Profile', 
                           form=form)


@app.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    """This view function handles post requests to follow users."""

    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if not user:
            flash("User {} not found.".format(username))
            return redirect(url_for('index'))
        
        if user == current_user:
            flash("You cannot follow yourself!")
        elif current_user.is_following(user):
            flash("You are already following {}.".format(username))
        else:
            current_user.follow(user)
            db.session.commit()
            flash("You are now following {}.".format(username))
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))


@app.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    """This view function handles post requests to unfollow users."""

    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if not user:
            flash("User {} not found.".format(username))
            return redirect(url_for('index'))
        
        if user == current_user:
            flash("You cannot unfollow yourself!")
        elif not current_user.is_following(user):
            flash("You were not following {}.".format(username))
        else:
            current_user.unfollow(user)
            db.session.commit()
            flash("You are not longer following {}.".format(username))
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))


@app.route('/explore')
@login_required
def explore():
    """This view function handles requests to explore all user posts."""

    posts = Post.query.order_by(Post.timestamp.desc()).all()

    return render_template('index.html', title='Explore', posts=posts)
