from flask import render_template, flash, redirect, url_for, request, g, \
    jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
from langdetect import detect, LangDetectException
from app import db
from app.models import User, Post
from app.translate import translate
from app.main import bp
from app.main.forms import EditProfileForm, EmptyForm, SubmitPostForm, \
    SearchForm


@bp.before_request
def before_request():
    """
    This function handles operations to perform before each request, 
    registered with the app.
    """

    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        g.search_form = SearchForm()

    # save the best supported language to g for post translation rendering
    g.locale = request.accept_languages.best


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    """This function implements the view logic for the index page."""

    page = request.args.get('page', 1, type=int)
    posts = current_user.followed_posts().paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.index', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.index', page=posts.prev_num) \
        if posts.has_prev else None

    form = SubmitPostForm()
    if form.validate_on_submit():
        try:
            language = detect(form.post.data)
        except LangDetectException:
            language = ''
        post = Post(body=form.post.data, author=current_user, 
                    language=language)
        db.session.add(post)
        db.session.commit()
        flash("Your new post is now live!")
        return redirect(url_for('main.index'))

    return render_template('index.html', title='Home', posts=posts.items, 
                           form=form, next_url=next_url, prev_url=prev_url)


@bp.route('/user/<username>')
@login_required
def user(username):
    """This view function implements the logic to display user profiles."""

    user = User.query.filter_by(username=username).first_or_404()
    form = EmptyForm()

    page = request.args.get('page', 1, type=int)
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.user', username=username, page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.user', username=username, page=posts.prev_num) \
        if posts.has_prev else None
    
    return render_template('user.html', title='User Profile', user=user, 
                           form=form, posts=posts.items, next_url=next_url,
                           prev_url=prev_url)


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """This view function implements the logic to edit user profiles."""

    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash("Your profile has been updated successfully!")
        return redirect(url_for('main.edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    
    return render_template('edit_profile.html', title='Edit Profile', 
                           form=form)


@bp.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    """This view function handles post requests to follow users."""

    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if not user:
            flash("User {} not found.".format(username))
            return redirect(url_for('main.index'))
        
        if user == current_user:
            flash("You cannot follow yourself!")
        elif current_user.is_following(user):
            flash("You are already following {}.".format(username))
        else:
            current_user.follow(user)
            db.session.commit()
            flash("You are now following {}.".format(username))
        return redirect(url_for('main.user', username=username))
    else:
        return redirect(url_for('main.index'))


@bp.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    """This view function handles post requests to unfollow users."""

    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if not user:
            flash("User {} not found.".format(username))
            return redirect(url_for('main.index'))
        
        if user == current_user:
            flash("You cannot unfollow yourself!")
        elif not current_user.is_following(user):
            flash("You were not following {}.".format(username))
        else:
            current_user.unfollow(user)
            db.session.commit()
            flash("You are not longer following {}.".format(username))
        return redirect(url_for('main.user', username=username))
    else:
        return redirect(url_for('main.index'))


@bp.route('/explore')
@login_required
def explore():
    """This view function handles requests to explore all user posts."""

    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.explore', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.explore', page=posts.prev_num) \
        if posts.has_prev else None

    return render_template('index.html', title='Explore', posts=posts.items, 
                           next_url=next_url, prev_url=prev_url)


@bp.route('/translation', methods=['POST'])
@login_required
def translation():
    """
    This view function handles post requests only to translate user posts.
    """

    return jsonify(
        {'text': translate(text=request.form['text'],
                           source_language=request.form['source_language'],
                           dest_language=request.form['dest_language'])})


@bp.route('/search')
def search():
    """
    This view function handles requests to search user posts and display 
    search results.
    """

    # temp code for debugging
    flash('Search text submitted - {}'.format(request.args.get('q')))
    return redirect(url_for('main.index'))
