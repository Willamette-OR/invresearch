import requests
from datetime import datetime
from flask import current_app


def symbol_search(query, page, stocks_per_page):
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


def company_profile(symbol):
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


def quote(symbol):
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


def financials_history(symbol):
    """
    This function gets historical data for stock financials, and returns the 
    data in a json payload.

    Note:
        It currently uses the GuruFocus API for data.
    """

    return get_guru_data(symbol, data_type='financials')
