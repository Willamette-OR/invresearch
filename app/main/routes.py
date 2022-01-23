import os
from flask import render_template, flash, redirect, url_for, request, g, \
    jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
from langdetect import detect, LangDetectException
from app import db
from app.models import Notification, User, Post, Message
from app.translate import translate
from app.main import bp
from app.main.forms import EditProfileForm, EmptyForm, SubmitPostForm, \
    SearchForm, MessageForm


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

    # forms for posts
    form = SubmitPostForm()
    if form.validate_on_submit():
        try:
            language = detect(form.post.data)
        except LangDetectException:
            language = ''
        post = Post(body=form.post.data, author=current_user, 
                    language=language)
        if form.parent_id.data:
            post.parent_id = int(form.parent_id.data)
        db.session.add(post)
        db.session.commit()
        flash("Your new post is now live!")
        return redirect(url_for('main.index'))

    return render_template('index.html', title='Home', posts=posts.items, 
                           form=form, allow_new_op=True, next_url=next_url, 
                           prev_url=prev_url)


@bp.route('/user/<username>')
@login_required
def user(username):
    """This view function implements the logic to display user profiles."""

    user = User.query.filter_by(username=username).first_or_404()
    empty_form = EmptyForm()

    page = request.args.get('page', 1, type=int)
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.user', username=username, page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.user', username=username, page=posts.prev_num) \
        if posts.has_prev else None

    # forms for posts
    form = SubmitPostForm()
    if form.validate_on_submit():
        try:
            language = detect(form.post.data)
        except LangDetectException:
            language = ''
        post = Post(body=form.post.data, author=current_user, 
                    language=language)
        if form.parent_id.data:
            post.parent_id = int(form.parent_id.data)
        db.session.add(post)
        db.session.commit()
        flash("Your new post is now live!")
        return redirect(url_for('main.index'))
    
    return render_template('user.html', title='User Profile', user=user, 
                           empty_form=empty_form, posts=posts.items, 
                           next_url=next_url, prev_url=prev_url, form=form)


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """This view function implements the logic to edit user profiles."""

    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data

        avatar_file = form.avatar.data
        if avatar_file:
            avatar_file.save(
                os.path.join('app/static/avatars', current_user.get_id()))

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


@bp.route('/explore', methods=['GET', 'POST'])
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

    # forms for posts
    form = SubmitPostForm()
    if form.validate_on_submit():
        try:
            language = detect(form.post.data)
        except LangDetectException:
            language = ''
        post = Post(body=form.post.data, author=current_user, 
                    language=language)
        if form.parent_id.data:
            post.parent_id = int(form.parent_id.data)
        db.session.add(post)
        db.session.commit()
        flash("Your new reply is now live!")
        return redirect(url_for('main.explore'))

    return render_template('index.html', title='Explore', posts=posts.items, 
                           next_url=next_url, prev_url=prev_url, form=form, 
                           allow_new_op=False)


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
@login_required
def search():
    """
    This view function handles requests to search user posts and display 
    search results.
    """

    # currently if the search is empty just redirect to explore
    # notice that the form method used here is NOT "validate_on_submit",
    # but instead "validate".
    # the reason is "validate_on_submit" is for POST methods only,
    # while the search form uses GET.
    if not g.search_form.validate():
        return redirect(url_for('main.explore'))

    # grab parameters from the request and perform user post search
    page = request.args.get('page', 1, type=int)
    query = g.search_form.q.data
    posts, total = Post.search(expression=query, page=page, 
                               per_page=current_app.config['POSTS_PER_PAGE'])

    # generate urls for pagination
    next_url = url_for('main.search', q=query, page=(page + 1)) \
        if page * current_app.config['POSTS_PER_PAGE'] < total else None
    prev_url = url_for('main.search', q=query, page=(page - 1)) \
        if page > 1 else None

    return render_template('search.html', title='Search Results', posts=posts, 
                           next_url=next_url, prev_url=prev_url)


@bp.route('/user/<username>/popup')
@login_required
def user_popup(username):
    """This view function handles Ajax requests to display user information."""

    user = User.query.filter_by(username=username).first_or_404()
    form = EmptyForm()
    
    return render_template('user_popup.html', user=user, form=form)


@bp.route('/send_message/<recipient>', methods=['GET', 'POST'])
@login_required
def send_message(recipient):
    """This view function handles requests to message users."""

    user = User.query.filter_by(username=recipient).first_or_404()
    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(body=form.body.data, author=current_user, recipient=user)
        db.session.add(msg)
        user.add_notification(name='unread_message_count', 
                              data=user.new_messages())
        db.session.commit()
        flash('Your message to {} has been sent.'.format(recipient))
        return redirect(url_for('main.user', username=recipient))

    return render_template('send_message.html', title='Send Message', 
                           recipient=recipient, form=form)


@bp.route('/messages')
@login_required
def messages():
    """This view function handles requests to view received messages."""

    current_user.last_message_read_time = datetime.utcnow()
    current_user.add_notification(name='unread_message_count', data=0)
    db.session.commit()

    page = request.args.get('page', 1, type=int)
    messages = current_user.received_messages.order_by(
        Message.timestamp.desc()).paginate(
            page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.messages', page=messages.next_num) \
        if messages.has_next else None
    prev_url = url_for('main.messages', page=messages.prev_num) \
        if messages.has_prev else None

    return render_template('messages.html', title='Messages', 
                           messages=messages.items, next_url=next_url, 
                           prev_url=prev_url)


@bp.route('/notifications')
@login_required
def notifications():
    """
    This view function handles requests to return notifications added/updated 
    since a given point in time.

    The time value of the given point in time is stored in the url argument 
    'since'.
    """

    since = request.args.get('since', 0.0, type=float)

    notifications = current_user.notifications.filter(
        Notification.timestamp > since).order_by(Notification.timestamp.asc())

    return jsonify([{
        'name': n.name,
        'data': n.get_data(),
        'timestamp': n.timestamp
    } for n in notifications])


@bp.route('/export_posts')
@login_required
def export_posts():
    """
    This view function handles requests to export the current user's posts.
    """

    if current_user.get_task_in_progress('export_posts'):
        flash('A user post exporting task is currently in progress.')
    else:
        current_user.launch_task('export_posts', 'Exporting posts...')
        db.session.commit()

    return redirect(url_for('main.user', username=current_user.username))
