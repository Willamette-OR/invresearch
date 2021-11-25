import requests
from datetime import datetime
from flask import current_app
from yahoo_fin import stock_info


def search_stocks_by_symbol(query, page, stocks_per_page):
    """
    This function searches for matching stocks given the input query string.

    It returns a list of results given the specified page # and number per 
    page.

    It currently uses the symbol_lookup API from Finnhub.

    TODO - think of ways to cache the search results for pagination, to 
    minimize the # of API requests when users paging through search results.
    """

    # check if the api client has been configured
    if not current_app.finnhub_client:
        return [], 0

    # perform the search via an API
    response = current_app.finnhub_client.symbol_lookup(query)
    
    # prepare the search results
    total = response['count']
    if not isinstance(page, int) or page < 1:
        raise ValueError("Invalidate page value.")
    elif (page - 1) * stocks_per_page < total:
        matched_symbols = response['result'][
            ((page - 1) * stocks_per_page):min(page * stocks_per_page, total)]
    else:
        matched_symbols = []
        
    return matched_symbols, total


def get_company_profile(symbol):
    """
    This function get company info for a given symbol.
    It returns None if the symbol does not exist.

    It currently uses the company_profile2 API from Finnhub.
    """

    # check if the api client has been configured
    if not current_app.finnhub_client:
        return None

    # fetch company profile from Finnhub
    response = current_app.finnhub_client.company_profile2(symbol=symbol)
    if len(response) == 0:
        return None

    # prepare the company profile payload
    profile_payload = {}
    profile_payload['name'] = response['name']

    return profile_payload


def get_quote(symbol):
    """
    This function gets quote for a given symbol.
    It returns None if the symbol does not exist.
    
    It currently uses the quote API from Finnhub.
    """

    # check if the api client has been configured
    if not current_app.finnhub_client:
        return None

    payload = current_app.finnhub_client.quote(symbol)

    # set the currency to USD for all, since the Finnhub API 
    # always defaults it to USD in its response
    payload['currency'] = 'USD'

    # also convert the epoch number of the time field to a python datetime 
    # string, since the Finnhub API always defaults the market time to an 
    # epoch value in its response
    payload['t'] = str(datetime.fromtimestamp(int(payload['t'])))

    return payload


def get_guru_data(symbol, data_type):
    """
    This helper function pulls data via the GuruFocus API, for the given symbol
    and data type.

    Input:
        symbol: stock ticker symbol
        data_type: possible values include:
            'financials'
            'analyst_estimate'
            ...
            (for more choices, checkout the API documentation here:
            https://www.gurufocus.com/api.php)
    """

    api_token = current_app.config['GURU_API_KEY']
    base_url = 'https://api.gurufocus.com/public/user/' + api_token + '/stock/'
    constructed_url = base_url + symbol + '/' + data_type
    
    r = requests.get(constructed_url)
    if r.status_code != 200:
        return "Error: the GuruFocus API service failed."
    else:
        return r.json()


# a lookup to find section names specifically in the Guru financials payload by 
# metric names
section_lookup_by_metric = {
        'EBITDA': 'income_statement',
        'EBIT': 'income_statement',
        'Net Income': 'income_statement'
    }


def get_financials_history(symbol):
    """
    This function gets historical data for stock financials, and returns the 
    data in a json payload.

    Note:
        It currently uses the GuruFocus API for data.
    """

    return get_guru_data(symbol, data_type='financials')


def get_analyst_estimates(symbol):
    """
    This function gets analyst estimates data, and returns the data in a json 
    payload.

    Note:
        It currently use the GuruFocus API for data.
    """

    return get_guru_data(symbol, data_type='analyst_estimate')


def get_quote_history(symbol, start_date=None, end_date=None, interval='1mo', 
                      header='close'):
    """
    This function pulls historical quote data, and returns the cleaned up data 
    in a dictionary of "<timestamp>: <price>".

    By default, it will return the "closing" prices for all available 
    intervals.

    Inputs:
        'start_date': '%m/%d/%Y'
        'end_date': '%m/%d/%Y

    Note:
        It currently uses the "yahoo_fin" library for scraping historical data 
        from Yahoo Finance.
        For more details, check out the author's documentation here:
        https://theautomatic.net/yahoo_fin-documentation/ 
    """

    # get the quote history in Pandas dataframe via a web scraper
    df_quote_history = stock_info.get_data(symbol, 
                                           start_date=start_date, 
                                           end_date=end_date, 
                                           interval=interval)

    # construct the output dictionary of "<timestamp>: <price>"
    data = {}
    df_selected_price = df_quote_history[header]
    for timestamp in dict(df_selected_price):
        data[timestamp.to_pydatetime()] = df_selected_price[timestamp]

    return data


def get_quote_details(symbol):
    """
    This function pulls quote details from the web and returns the data in a 
    dictionary.

    Inputs:
        'symbol': the ticker symbol of stocks, e.g., 'AAPL', 'AMZN', etc. It is 
                  not case sensitive.

    Notes:
        This function currently uses the "yahoo_fin" library for scraping 
        historical data from Yahoo Finance.

        For more details, check out the author's documentation here: 
        https://theautomatic.net/yahoo_fin-documentation/#get_quote_table 
    """

    try:
        # download data
        data_downloaded = stock_info.get_quote_table(symbol)

        # return the downloaded data if it's a dictionary, otherwise raise an
        # exception
        if isinstance(data_downloaded, dict):
            # standardize the downloaded data - this is API specific
            data = {}
            data['Market Cap'] = data_downloaded['Market Cap']
            data['Beta (5Y Monthly)'] = data_downloaded['Beta (5Y Monthly)']
            data['52 Week Range'] = data_downloaded['52 Week Range']
            data['Earnings Date'] = data_downloaded['Earnings Date']
            data['Ex-Dividend Date'] = data_downloaded['Ex-Dividend Date']
            data['Forward Dividend & Yield'] = \
                data_downloaded['Forward Dividend & Yield']

            return data
        else:
            raise TypeError("Invalid data type for quote details - only dict "
                            "is accepted.")

    except:
        # raise a more informational exception
        raise ConnectionAbortedError('Unable to download quote details data.')
