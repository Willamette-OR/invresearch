from app.stocks.metrics import Metric


section_lookup = {
    'Equity-to-Asset': 'common_size_ratios',
    'Debt-to-Asset': 'common_size_ratios'
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


def get_fundamental_indicators(financials_history, start_date):
    """
    This function gets raw data from the input financials history data after a 
    pre-specified start date,creates and returns a dictionary of indicators 
    needed for stocks' fundamental analysis.

    Inputs:
        'financials_history': data of a stock's financials history
        'start_date': the early date since when data in the input financials
                      history will be considered
    """

    data_indicators = {}

    # Debt-to-Asset
    # save the TTM value
    _name = 'Debt-to-Asset'
    data_indicators[_name] = get_metric(name=_name, 
                                        financials_history=financials_history, 
                                        start_date=start_date).TTM_value

    return data_indicators
