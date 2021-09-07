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

    # fetch and return quote from Finnhub
    return current_app.finnhub_client.quote(symbol)
