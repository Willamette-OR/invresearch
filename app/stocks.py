from flask import current_app


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

    # fetch quote from Finnhub
    response = current_app.finnhub_client.quote(symbol)
    
    # prepare the quote payload
    quote_payload = {}
    quote_payload['current_price'] = response['c']
    if quote_payload['current_price'] == 0:
        return None

    return quote_payload
