import json
import re
from time import time
from datetime import datetime
from langdetect import detect, LangDetectException
from flask import flash, redirect, url_for, render_template, request, \
                  current_app, g, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Stock, StockNote, Post
from app.main.forms import EmptyForm, SearchForm, SubmitPostForm
from app.stocksdata import get_company_profile, search_stocks_by_symbol, \
                           section_lookup_by_metric
from app.fundamental_analysis import get_estimated_return, \
                                     get_fundamental_start_date
from app.stocks import bp
from app.stocks.plot import get_valplot_dates, get_durations, \
                            get_normal_price, stock_valuation_plot, \
                            timeseries_plot
from app.stocks.forms import NoteForm, CompareForm


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


@bp.route('/stock/<symbol>', methods=['GET', 'POST'])
@login_required
def stock(symbol):
    """
    This view function handles requests to view the stock profile of a given 
    symbol.
    """

    ######################
    # Retrieve the stock #
    ######################

    # look up the symbol in the stock database
    symbol_upper = symbol.upper()
    stock = Stock.query.filter_by(symbol=symbol_upper).first()

    # fetch the stock info and add it to the app database if it has not been 
    # added
    if not stock:
        profile_data = get_company_profile(symbol_upper)
        if not profile_data:
            flash("The stock symbol {} does not exist..." 
                  "Please double check.".format(symbol_upper))
            return redirect(url_for('main.index'))
        else:
            stock = Stock(symbol=symbol_upper, name=profile_data['name'])
            db.session.add(stock)
            db.session.commit()

    ####################
    # Update the quote #
    ####################

    stock.update_quote()
    db.session.commit()

    ################
    # Handle forms #
    ################

    # define an empty Flask form to validate post requests for 
    # watching/unwatching stocks
    empty_form = EmptyForm()

    # get existing notes
    current_note = StockNote.query.filter_by(
        user=current_user, stock=stock).first()

    # form logic for user notes
    note_form = NoteForm()
    if note_form.validate_on_submit():
        # delete the existing note first if any
        StockNote.query.filter_by(user=current_user, stock=stock).delete()
        note = StockNote(body=note_form.body.data, user=current_user, 
                         stock=stock)
        db.session.add(note)
        db.session.commit()
        flash("Your notes have been saved/updated successfully!")
        return redirect(url_for('stocks.stock', symbol=symbol))
    elif request.method == 'GET':
        note_form.body.data = \
            current_note.body if current_note is not None else None

    #############################
    # Process request arguments #
    #############################

    # get input parameters from the request
    num_of_years = request.args.get('num_of_years', 20, type=int)
    valuation_metric = request.args.get(
        'valuation_metric', 
        current_app.config['STOCK_VALUATION_METRIC_DEFAULT'], 
        type=str)
    payload_only = request.args.get('payload_only', 0, type=int)

    ###############
    # Posts logic #
    ###############

    # get posts for the requested page
    page = request.args.get('page', 1, type=int)
    posts = stock.get_posts().paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for(
        'stocks.stock', symbol=stock.symbol, page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for(
        'stocks.stock', symbol=stock.symbol, page=posts.prev_num) \
        if posts.has_prev else None

    # handle the post form
    form = SubmitPostForm()
    if form.validate_on_submit():
        try:
            language = detect(form.post.data)
        except LangDetectException:
            language = ''
        post = Post(
            body=form.post.data, author=current_user, stock=stock, 
            language=language)
        if form.parent_id.data:
            post.parent_id = int(form.parent_id.data)
        db.session.add(post)
        db.session.commit()
        flash("Your new post for stock {} is now live!".format(stock.symbol))
        return redirect(url_for('stocks.stock', symbol=stock.symbol))

    #######################################################################
    # Prep for valuation plotting, quote details and fundamental analysis #
    #######################################################################

    # get stock data needed for valuation plotting
    quote_history = stock.get_quote_history_data(
        start_date='01-01-1800', end_date='01-01-9999')
    financials_history = stock.get_financials_history_data()
    analyst_estimates = stock.get_analyst_estimates_data()
    quote_details = stock.get_quote_details_data()

    # get dates needed for valuation plotting, the subset of quote history data 
    # to be used for plotting
    start_date_quote_history, start_date_financials_history, end_date, _ = \
        get_valplot_dates(
            quote_history=quote_history, financials_history=financials_history, 
            num_of_years=num_of_years)
    quote_history_valplotting = \
        stock.get_quote_history_data(start_date=start_date_quote_history, 
                                     end_date=end_date)

    # get fundamental indicators, using the financials history data from the 
    # same time window as that used for valuation plotting
    # TODO - check if a different start date for the financials history data 
    # should be used when getting fundamental indicators
    fundamental_indicators = stock.get_fundamental_indicator_data()

    # get the historical average price multiple with respect to the chosen 
    # metric, and the associated normal prices
    average_price_multiple, normal_price_data, valuation_metric_data = \
        get_normal_price(
            metric_name=valuation_metric,
            section_name=section_lookup_by_metric[valuation_metric],
            start_date=start_date_financials_history,
            quote_history_data=quote_history_valplotting,
            financials_history=financials_history,
            analyst_estimates=analyst_estimates
        )

    # return if not enough data was available to calculate the average 
    # historical price multiple
    if not average_price_multiple:

        if payload_only:
            # return an otherwise empty payload, except for a flag indicating 
            # no valid plot in the paylod 
            plot = {}
            plot['valid_plot'] = 0

            return jsonify(plot)

        return render_template(
            'stocks/stock.html', title="Stock - {}".format(stock.symbol), 
            stock=stock, quote=json.loads(stock.quote_payload), 
            empty_form=empty_form, 
            quote_details=quote_details, 
            fundamental_indicators=fundamental_indicators, note_form=note_form,
            current_note=current_note,
            allow_new_op=True, form=form, posts=posts.items, next_url=next_url, 
            prev_url=prev_url, post_links=True 
        )

    # get the plot payload 
    plot = stock_valuation_plot(quote_history_data=quote_history_valplotting,
                                normal_price_data=normal_price_data,
                                average_price_multiple=average_price_multiple)

    # add a flag to the paylod indicating a valid plot
    plot['valid_plot'] = 1

    # add to the paylod the updated estimated return, specific to the updated 
    # valuation plot 
    plot['estimated_return'] = \
        get_estimated_return(quote_history_data=quote_history_valplotting, 
                             normal_price_data=normal_price_data, 
                             dividend_yield=stock.dividend_yield)

    # add to the paylod the data of the associated valuation metric
    plot['valuation_metric_data'] = {
        timestamp.strftime('%m%y'): valuation_metric_data[timestamp] 
        for timestamp in valuation_metric_data}

    #################################################
    # Return only the plot payload for if requested #
    #################################################
    
    if payload_only:
        return jsonify(plot)

    #########################################################
    # Get acceptable durations for stock valuation plotting #
    #########################################################

    durations = get_durations(quote_history=quote_history, 
                              financials_history=financials_history)

    ############################
    # Return the full template #
    ############################

    return render_template(
        'stocks/stock.html', title="Stock - {}".format(stock.symbol), 
        stock=stock, quote=json.loads(stock.quote_payload), 
        empty_form=empty_form, 
        plot=plot, durations=durations, 
        valuation_metric=valuation_metric, quote_details=quote_details,
        fundamental_indicators=fundamental_indicators,
        note_form=note_form,
        current_note=current_note,
        allow_new_op=True, form=form, posts=posts.items, next_url=next_url, 
        prev_url=prev_url, post_links=True
    )


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
            return redirect(url_for('stocks.stock', symbol=symbol))
        
        # watch the stock and update the database
        if current_user.is_watching(stock):
            flash("You are already following this stock!")
        else:
            current_user.watch(stock)
            db.session.commit()
            flash("You are now watching {} ({})!".format(stock.name, 
                                                         stock.symbol))
        
    # redirect to the stock's profile page regardless
    return redirect(url_for('stocks.stock', symbol=symbol))


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
            return redirect(url_for('stocks.stock', symbol=symbol))

        # unwatch the stock if the user is currently watching it
        if current_user.is_watching(stock):
            current_user.unwatch(stock)
            db.session.commit()
            flash("You are no longer watching {} ({})!".format(stock.name, 
                                                                stock.symbol))
        else:
            flash("You cannot unwatch a stock you did not watch.")

    # redirect to the stock profile page regardless
    return redirect(url_for('stocks.stock', symbol=symbol))


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

    return render_template('stocks/watchlist.html', title='Watchlist', 
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
    stocks, total = \
        search_stocks_by_symbol(g.search_form.q.data, page, 
                                current_app.config['POSTS_PER_PAGE'])

    # output a message if no stocks are returned
    if total == 0:
        flash("No stocks can be found for '{}'.".format(g.search_form.q.data))

    # prep for pagination
    next_url = url_for(
        'stocks.search_stocks', q=g.search_form.q.data, page=(page+1)) \
            if page * current_app.config['POSTS_PER_PAGE'] < total else None
    prev_url = url_for(
        'stocks.search_stocks', q=g.search_form.q.data, page=(page-1)) \
            if page > 1 else None

    return render_template('stocks/search_stocks.html', title='Search Results',
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


@bp.route('/stock/<main_symbol>/metric_profile/<indicator_name>', 
          methods=['GET', 'POST'])
@login_required
def metric_profile(main_symbol, indicator_name):
    """
    This view function handles requests to view the profile of a given 
    financial metric for a pre-specified stock.
    """

    # get request arguments
    payload_only = request.args.get('payload_only', 0, type=int)
    num_of_years = request.args.get('num_of_years', 20, type=int) 

    # default the symbols of stocks for metric comparison to None, unless some 
    # form data including a list of stock symbols is posted via Ajax ;
    # while None, only the stock associated with the main symbol will be 
    # processed and plotted later
    symbols_to_compare = None

    # initialize the form for comparing the values of the same metric of 
    # different stocks, and if validated get stock symbols from the form data
    compare_form = CompareForm()
    if compare_form.validate_on_submit():

        # extract a list of symbols from the form data posted via Ajax;
        # the symbols included in the form posted string can be delimited by
        # ",", ";", or "<space>"
        symbols_to_compare = [symbol.strip().upper() for symbol in 
                              re.split('[,; ]', compare_form.symbols.data) 
                              if symbol]

        # set this flag to 1 so that only a data payload will be returned to 
        # the Ajax function later to dynamically update the plot
        payload_only = 1

    # derive a start date that'll give by default 20 years of 
    # financials history
    stock = Stock.query.filter_by(symbol=main_symbol).first_or_404()
    start_date = get_fundamental_start_date(
        num_of_years=num_of_years, 
        last_report_date=stock.get_last_financials_report_date())

    # form a list of symbols to loop through for processing and preparing for 
    # metric time series plotting
    symbols = symbols_to_compare + [main_symbol] if symbols_to_compare \
                                                 else [main_symbol]

    # initialize lists to separately hold valid stock symbols and associated 
    # data (in the form of dictionaries) for plotting
    symbols_valid = []
    symbols_invalid = []
    plot_dicts_valid = []

    # loop through all input symbols
    for symbol in symbols:

        # retrieve the stock database object
        stock = Stock.query.filter_by(symbol=symbol).first()

        # fetch the stock info and add it to the app database if it has not been 
        # added
        if not stock:
            profile_data = get_company_profile(symbol)
            if not profile_data:
                # skip to the next symbol on the list if stock not found
                symbols_invalid.append(symbol)
                continue
            else:
                stock = Stock(symbol=symbol, name=profile_data['name'])
                db.session.add(stock)
                db.session.commit()

        # if a corresponding stock can be found, the symbol is appended to the 
        # list of valid symbols; 
        # this list will later be rendered as legends in the metric plot
        symbols_valid.append(symbol)        

        # get all fundamental indicators filtered by dates
        indicators_data = stock.get_fundamental_indicator_data(
            start_date=start_date.strftime('%m-%d-%Y'), debug=True)
    
        # get the payload of the pre-specified indicator
        try:
            indicator_data = [
                indicators_data[section][name]
                for section in indicators_data 
                for name in indicators_data[section] 
                if name==indicator_name
            ][0]
        except IndexError:
            flash('Unable to find metric: {}.'.format(indicator_name))
            return redirect(url_for('stocks.stock', symbol=stock.symbol))

        # get data of the underlying metric out of the indicator payload
        metric = indicator_data['Object']

        # prepare for plotting
        plot_dicts_valid.append(dict(zip(metric.timestamps, metric.values)))

        # some additional derivations; only needed for the stock corresponding 
        # to the main symbol passed as an argument in the url
        if symbol == main_symbol:

            # get data of the metric used for 'rating" calculations, in case 
            # this metric is different from the underlying metric
            rated_metric = indicator_data['Rating']['object']

            # get some basic statistics of the underlying metric
            rated_metric.min_10y, rated_metric.max_10y, \
                rated_metric.median_10y, rated_metric.pctrank_of_latest_10y = \
                rated_metric.get_range_info()

    # plot the metric time series, for a valid list of stocks
    plot, table_data = timeseries_plot(
        name=metric.name, 
        data_list=plot_dicts_valid, 
        symbols=symbols_valid, 
        start_date=start_date
    )

    if payload_only:
        # TODO - add the table data to this payload, after converting the 
        # format of timestamps to strings
        payload = {
            'plot': plot,
            'symbols_invalid': json.dumps(symbols_invalid)
            }
        return jsonify(payload)
    else:
        return render_template(
            'stocks/metric.html', title=stock.symbol + ': '+ metric.name, 
            stock=stock, metric=metric, rated_metric=rated_metric, 
            compare_form=compare_form,
            indicator_data=indicator_data, indicator_name=indicator_name, 
            format_type=indicator_data['Type'], plot=plot, table_data=table_data
        )
