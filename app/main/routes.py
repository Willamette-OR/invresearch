from flask import render_template, flash, redirect, url_for, request, g, \
    jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime
from time import time
from langdetect import detect, LangDetectException
import json
from app import db
from app.models import Notification, User, Post, Message, Stock
from app.translate import translate
from app.main import bp
from app.main.forms import EditProfileForm, EmptyForm, SubmitPostForm, \
    SearchForm, MessageForm
from app.stocks import company_profile, quote, symbol_search
from app.plot import stock_valuation_plot, get_normal_price


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


@bp.route('/stock/<symbol>')
@login_required
def stock(symbol):
    """
    This view function handles requests to view the stock profile of a given symbol.
    """

    # look up the symbol in the app database
    symbol_upper = symbol.upper()
    stock = Stock.query.filter_by(symbol=symbol_upper).first()

    # fetch the stock info and add it to the app database if it has not been 
    # added
    if not stock:
        profile_data = company_profile(symbol_upper)
        if not profile_data:
            flash("The stock symbol {} does not exist..." 
                  "Please double check.".format(symbol_upper))
            return redirect(url_for('main.index'))
        else:
            stock = Stock(symbol=symbol_upper, name=profile_data['name'])
            db.session.add(stock)
            db.session.commit()

    # update the quote
    stock.update_quote()
    db.session.commit()
    
    # define an empty Flask form to validate post requests for 
    # watching/unwatching stocks
    form = EmptyForm()

    # set up for a stock valuation graph, with timestamps on the x axis and 
    # quote history and "normal prices" on the y axis
    # TODO - replace the hard coded start and end dates with a logic where the 
    # date filters are affected by user inputs

    # get the quote history, the financials history, and the analyst estimates 
    # first
    _start_date = '01-01-2007'
    _end_date = '11-17-2021'
    _start_date_normal_price = '01-01-2006'
    quote_history_data = stock.get_quote_history_data(start_date=_start_date, 
                                                      end_date=_end_date)
    financials_history = stock.get_financials_history_data()
    analyst_estimates = stock.get_analyst_estimates_data()

    # get the historical average price multiple with respect to the chosen 
    # metric, and the associated normal prices
    # TODO - replace the hard coded metric name with a logic where the metric 
    # can be chosen by the users
    average_price_multiple, normal_price_data = get_normal_price(
        metric_name='EBITDA',
        section_name='income_statement',
        start_date=_start_date_normal_price,
        quote_history_data=quote_history_data,
        financials_history=financials_history,
        analyst_estimates=analyst_estimates
    )

    # get the plot payload 
    plot = stock_valuation_plot(quote_history_data=quote_history_data,
                                normal_price_data=normal_price_data,
                                average_price_multiple=average_price_multiple)

    return render_template(
        'stock.html', title="Stock - {}".format(stock.symbol), stock=stock, 
        quote=json.loads(stock.quote_payload), form=form, plot=plot)
    

@bp.route('/watch/<symbol>', methods=['POST'])
@login_required
def watch(symbol):
    """
    This view function handles POST requests to watch the stock given 
    a specified symbol.
    """

    # use an empty form to validate the request to watch
    form = EmptyForm()

    if form.validate_on_submit():
        # query the stock object, and return a 404 if it does not exit
        stock = Stock.query.filter_by(symbol=symbol).first()
        if not stock:
            flash("The stock you want to watch is not currently in our "
                  "database.")
            flash("Attempting to fetch the stock from the internet...")
            return redirect(url_for('main.stock', symbol=symbol))
        
        # watch the stock and update the database
        if current_user.is_watching(stock):
            flash("You are already following this stock!")
        else:
            current_user.watch(stock)
            db.session.commit()
            flash("You are now watching {} ({})!".format(stock.name, 
                                                         stock.symbol))
        
    # redirect to the stock's profile page regardless
    return redirect(url_for('main.stock', symbol=symbol))


@bp.route('/unwatch/<symbol>', methods=['POST'])
@login_required
def unwatch(symbol):
    """
    This view function handles requests to unfollow the stock given 
    a specified symbol.
    """

    # use an empty Flask form to validate the request to unwatch
    form = EmptyForm()

    # perform operations to unwatch the stock if the request is validated
    if form.validate_on_submit():
        # fetch the data object of the stock to unwatch
        stock = Stock.query.filter_by(symbol=symbol).first()
        if not stock:
            flash("The stock you want to watch is not currently in our "
                  "database.")
            flash("Attempting to fetch the stock from the internet...")
            return redirect(url_for('main.stock', symbol=symbol))

        # unwatch the stock if the user is currently watching it
        if current_user.is_watching(stock):
            current_user.unwatch(stock)
            db.session.commit()
            flash("You are no longer watching {} ({})!".format(stock.name, 
                                                                stock.symbol))
        else:
            flash("You cannot unwatch a stock you did not watch.")

    # redirect to the stock profile page regardless
    return redirect(url_for('main.stock', symbol=symbol))


@bp.route('/watchlist')
@login_required
def watchlist():
    """
    This view function handles requests to view stocks in the user's watchlist.
    """

    stocks = current_user.watched.order_by(Stock.symbol.asc()).all()

    # only update quotes if the last quote was updated more than 
    # 300 seconds ago
    stock_quotes = []
    for stock in stocks:
        stock.update_quote(delay=300)
        db.session.commit()
        stock_quotes.append({'stock': stock, 
                             'quote': json.loads(stock.quote_payload)})

    # kick off a background task for quote polling if the task doesn't exist, 
    # and the watchlist is not empty
    if len(stocks) > 0:
        task_name = 'refresh_quotes'
        task_description = 'watchlist'
        task = current_user.tasks.filter_by(name=task_name, 
                                            description=task_description, 
                                            complete=False).first()
        if not task:
            current_user.launch_task(name=task_name, 
                                     description=task_description, 
                                     stocks=stocks,
                                     seconds=10,
                                     job_timeout=1200)
            db.session.commit()

    return render_template('watchlist.html', title='Watchlist', 
                           user=current_user, stock_quotes=stock_quotes)


@bp.route('/search_stocks')
@login_required
def search_stocks():
    """
    This view function handles requests to search for stocks and display 
    search results.
    """

    # redirect to the "explore" page if the GET-search form was empty
    if not g.search_form.validate():
        return redirect(url_for('main.explore'))

    # get search results for the requested page number
    page = request.args.get('page', 1, type=int)
    stocks, total = symbol_search(g.search_form.q.data, page, 
                                  current_app.config['POSTS_PER_PAGE'])

    # output a message if no stocks are returned
    if total == 0:
        flash("No stocks can be found for '{}'.".format(g.search_form.q.data))

    # prep for pagination
    next_url = url_for(
        'main.search_stocks', q=g.search_form.q.data, page=(page+1)) \
            if page * current_app.config['POSTS_PER_PAGE'] < total else None
    prev_url = url_for(
        'main.search_stocks', q=g.search_form.q.data, page=(page-1)) \
            if page > 1 else None

    return render_template('search_stocks.html', title='Search Results',
                           stocks=stocks, next_url=next_url, prev_url=prev_url)


@bp.route('/quote_polling')
@login_required
def quote_polling():
    """
    This view function handles Ajax requests to update and fetch the latest 
    quotes of stocks.
    
    Stock symbols are expected to be passed to this function via request 
    arguments.
    """

    # get arguments from the request
    symbol = request.args.get('symbol', '', type=str)
    delay = request.args.get('delay', 60, type=int)

    # use the symbol to locate the stock from the database
    stock = Stock.query.filter_by(symbol=symbol).first()
    if not stock:
        raise ValueError(
            'Unable to locate {} in the stock database.'.format(symbol))

    # update the quote for the located stock with a pre-specified delay 
    # (in seconds)
    stock.update_quote(delay=delay)
    db.session.commit()
    
    return jsonify({
        'quote': {'symbol': symbol,
                  'quote_payload': json.loads(stock.quote_payload)}
        })


@bp.route('/refresh_quote_polling')
@login_required
def refresh_quote_polling():
    """
    This view function handles client requests to tell the server that the 
    client is still active on a page with stock quotes to be updated.

    It takes an argument from the request to identify the quote refresh task 
    type, fetch the task and the associated job, and put into the job meta 
    data a timestamp for when the request is made.
    """

    task_desc = request.args.get('task_desc', None, type=str)
    if not task_desc:
        return

    # fetch the corresponding quote polling task & job
    task = current_user.tasks.filter_by(name='refresh_quotes', 
                                        description=task_desc, 
                                        complete=False).first()
    job = task.get_rq_job()

    # update the last ajax timestamp in the job metadata
    job.meta['last_ajax_timestamp_{}'.format(task_desc)] = time()
    job.save_meta()

    # return an "empty" response for the request
    return ('', 204)
