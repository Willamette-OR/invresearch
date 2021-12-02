import json
from time import time
from datetime import datetime
from flask import flash, redirect, url_for, render_template, request, \
                  current_app, g, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Stock
from app.main.forms import EmptyForm, SearchForm
from app.stocksdata import get_company_profile, search_stocks_by_symbol, \
                           section_lookup_by_metric
from app.stocks import bp
from app.stocks.plot import get_valplot_dates, get_durations, \
                            get_normal_price, stock_valuation_plot


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


@bp.route('/stock/<symbol>')
@login_required
def stock(symbol):
    """
    This view function handles requests to view the stock profile of a given 
    symbol.
    """

    # look up the symbol in the app database
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

    # update the quote
    stock.update_quote()
    db.session.commit()
    
    # define an empty Flask form to validate post requests for 
    # watching/unwatching stocks
    form = EmptyForm()

    # get the quote history, the financials history, the analyst estimates, and 
    # quote details
    start_date_quote_history, start_date_financials_history, end_date = \
        get_valplot_dates()
    quote_history_data = \
        stock.get_quote_history_data(start_date=start_date_quote_history, 
                                     end_date=end_date)
    financials_history = stock.get_financials_history_data()
    analyst_estimates = stock.get_analyst_estimates_data()
    quote_details = stock.get_quote_details_data()
    fundamental_indicators = stock.get_fundamental_indicator_data(
        start_date=start_date_financials_history)


    #######################################
    # Set up for stock valuation plotting #
    #######################################


    # get acceptable durations for stock valuation plotting;
    durations = get_durations(quote_history=quote_history_data, 
                              financials_history=financials_history)

    # get the historical average price multiple with respect to the chosen 
    # metric, and the associated normal prices;
    # the default metric to be used for valuation plotting can be changed in 
    # the app config file
    _valuation_metric = current_app.config['STOCK_VALUATION_METRIC_DEFAULT']
    average_price_multiple, normal_price_data = get_normal_price(
        metric_name=_valuation_metric,
        section_name=section_lookup_by_metric[_valuation_metric],
        start_date=start_date_financials_history,
        quote_history_data=quote_history_data,
        financials_history=financials_history,
        analyst_estimates=analyst_estimates
    )

    # return if not enough data was available to calculate the average 
    # historical price multiple
    if not average_price_multiple:
        return render_template(
            'stocks/stock.html', title="Stock - {}".format(stock.symbol), 
            stock=stock, quote=json.loads(stock.quote_payload), form=form, 
            quote_details=quote_details, 
            fundamental_indicators=fundamental_indicators
        )

    # get the plot payload 
    plot = stock_valuation_plot(quote_history_data=quote_history_data,
                                normal_price_data=normal_price_data,
                                average_price_multiple=average_price_multiple)


    ###################################
    # End of Valuation Plotting Setup #
    ###################################


    return render_template(
        'stocks/stock.html', title="Stock - {}".format(stock.symbol), 
        stock=stock, quote=json.loads(stock.quote_payload), form=form, 
        plot=plot, durations=durations, 
        valuation_metric=_valuation_metric, quote_details=quote_details,
        fundamental_indicators=fundamental_indicators
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


@bp.route('/update_valuation_plot')
@login_required
def update_valuation_plot():
    """
    This view function gets an updated stock valuation plot with pre-specified 
    input parameters, and returns scripts needed for plot rendering in a json 
    payload
    """

    # get input parameters from the request
    symbol = request.args.get('symbol').upper()
    num_of_years = request.args.get('num_of_years', 20, type=int)
    valuation_metric = request.args.get('valuation_metric', 'EBITDA', type=str)

    # query the stock object
    stock = Stock.query.filter_by(symbol=symbol).first_or_404()

    # get dates needed for valuation plotting
    start_date_quote_history, start_date_financials_history, end_date = \
        get_valplot_dates(num_of_years=num_of_years)

    # get stock data needed for valuation plotting
    quote_history_data = \
        stock.get_quote_history_data(start_date=start_date_quote_history, 
                                     end_date=end_date)
    financials_history = stock.get_financials_history_data()
    analyst_estimates = stock.get_analyst_estimates_data()

    # get the historical average price multiple with respect to the chosen 
    # metric, and the associated normal prices
    average_price_multiple, normal_price_data = get_normal_price(
        metric_name=valuation_metric,
        section_name=section_lookup_by_metric[valuation_metric],
        start_date=start_date_financials_history,
        quote_history_data=quote_history_data,
        financials_history=financials_history,
        analyst_estimates=analyst_estimates
    )

    # get the plot payload 
    plot = stock_valuation_plot(quote_history_data=quote_history_data,
                                normal_price_data=normal_price_data,
                                average_price_multiple=average_price_multiple)

    # return a json payload for Ajax requests
    return jsonify(plot)
