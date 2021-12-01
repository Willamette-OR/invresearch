from datetime import datetime
from app.stocks.metrics import Metric


section_lookup = {
    'Cash, Cash Equivalents, Marketable Securities': 'balance_sheet',
    'Short-Term Debt & Capital Lease Obligation': 'balance_sheet',
    'Long-Term Debt & Capital Lease Obligation': 'balance_sheet',
    'Equity-to-Asset': 'common_size_ratios'
}


def get_metric(name, financials_history, start_date):
    """
    This helper function extracts a metric's data from the financials history 
    data, based on the given metric name and start date of the financials 
    history to be considered.
    """

    return Metric(
        name=name, 
        timestamps=financials_history['financials']['annuals']['Fiscal Year'],
        values=financials_history['financials']['annuals']\
            [section_lookup[name]][name],
        start_date=start_date
    )


def get_fundamental_indicators(financials_history, 
                               start_date=datetime(1900, 1, 1)):
    """
    This function gets raw data from the input financials history data after a 
    pre-specified start date,creates and returns a dictionary of indicators 
    needed for stocks' fundamental analysis.

    Inputs:
        'financials_history': data of a stock's financials history
        'start_date': the early date since when data in the input financials
                      history will be considered - a Python's datetime object;
                      defaulted to be datetime(1900, 1, 1)
    """

    data_indicators = {}

    # Debt-to-Cash
    # save the TTM value
    _name = 'Debt-to-Cash'
    cash = get_metric(name='Cash, Cash Equivalents, Marketable Securities',
                      financials_history=financials_history,
                      start_date=start_date)
    short_term_debt = \
        get_metric(name='Short-Term Debt & Capital Lease Obligation',
                   financials_history=financials_history,
                   start_date=start_date)
    long_term_debt = \
        get_metric(name='Long-Term Debt & Capital Lease Obligation',
                   financials_history=financials_history,
                   start_date=start_date)
    _metric = (short_term_debt + long_term_debt) / cash
    data_indicators[_name] = _metric.TTM_value

    # Equity-to-Asset
    # save the TTM value
    _name = 'Equity-to-Asset'
    _metric = get_metric(name=_name, financials_history=financials_history, 
                         start_date=start_date)
    data_indicators[_name] = _metric.TTM_value

    # return the constructed dictionary
    return data_indicators
