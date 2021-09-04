from flask import current_app


def quote(symbol):
    """
    This function gets quote from a 3rd party API for a given symbol.
    
    It currently uses the quote API from Finnhub.
    """

    # fetch quote from Finnhub
    response = current_app.finnhub_client.quote(symbol)
    
    quote_data = {}
    quote_data['current_price'] = response['c']
    if quote_data['current_price'] == 0:
        return None

    return quote_data
