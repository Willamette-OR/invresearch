from datetime import datetime
from app.metrics import Metric


section_lookup = {
    'Cash, Cash Equivalents, Marketable Securities': 'balance_sheet',
    'Short-Term Debt & Capital Lease Obligation': 'balance_sheet',
    'Long-Term Debt & Capital Lease Obligation': 'balance_sheet',
    'Equity-to-Asset': 'common_size_ratios',
    'Debt-to-Equity': 'common_size_ratios',
    'EBITDA': 'income_statement',
    'Interest Coverage': 'valuation_and_quality',
    'Altman Z-Score': 'valuation_and_quality',
    'Revenue': 'income_statement',
    'Operating Income': 'income_statement',
    'Net Income': 'income_statement',
    'Cash Flow from Operations': 'cashflow_statement',
    'Gross Margin %': 'common_size_ratios',
    'Operating Margin %': 'common_size_ratios',
    'Net Margin %': 'common_size_ratios',
    'FCF Margin %': 'common_size_ratios',
    'ROE %': 'common_size_ratios'
}


def derive_debt_to_cash(name, financials_history, start_date):
    """
    This function derives and returns the metric for Debt-to-Cash.
    """

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
    debt_to_cash = (short_term_debt + long_term_debt) / cash
    debt_to_cash.name = name

    return debt_to_cash


def derive_debt_to_ebitda(name, financials_history, start_date):
    """
    This function derives and returns the metric for Debt-to-EBITDA.
    """

    short_term_debt = \
        get_metric(name='Short-Term Debt & Capital Lease Obligation',
                   financials_history=financials_history,
                   start_date=start_date)
    long_term_debt = \
        get_metric(name='Long-Term Debt & Capital Lease Obligation',
                   financials_history=financials_history,
                   start_date=start_date)
    ebitda = get_metric(name='EBITDA', financials_history=financials_history, 
                        start_date=start_date)
    debt_to_ebitda = (short_term_debt + long_term_debt) / ebitda
    debt_to_ebitda.name = name

    return debt_to_ebitda


def get_metric(name, financials_history, start_date, convert_to_numeric=True, 
               scale_factor=1.0, derive=None):
    """
    This helper function extracts a metric's data from the financials history 
    data, based on the given metric name and start date of the financials 
    history to be considered.
    """

    # if 'derive' function is given, derive the metric first
    if derive:
        return derive(name, financials_history, start_date)
    else:
        # get timestamps from the financials history payload
        timestamps = financials_history['financials']['annuals']['Fiscal Year']

        # get values from the financials history payload
        values = financials_history['financials']['annuals']\
                [section_lookup[name]].get(name)

        # manage edge cases of financial values (for insurance companies)
        fields_not_in_insurance = [
            'Altman Z-Score',
            'Operating Income',
            'Gross Margin %',
            'Operating Margin %'
        ]
        if name == 'Cash, Cash Equivalents, Marketable Securities' and values is None:
            values = financials_history['financials']['annuals']\
                     [section_lookup[name]].get(
                     'Balance Statement Cash and cash equivalents')
        elif name in fields_not_in_insurance and values is None:
            values = [0] * len(timestamps)          

        return Metric(
            name=name, 
            timestamps=timestamps,
            values=values,
            start_date=start_date,
            convert_to_numeric=convert_to_numeric,
            scale_factor=scale_factor
    )


_financial_strength_metrics_inputs = [
    {
        'name': 'Debt-to-Cash',
        'reverse': True,
        'derive': derive_debt_to_cash,
        'benchmark': None,
        'type': 'float',
        'scale_factor': 1.0
    },
    {
        'name': 'Equity-to-Asset',
        'reverse': False,
        'derive': None,
        'benchmark': None,
        'type': 'float',
        'scale_factor': 1.0
    },
    {
        'name': 'Debt-to-Equity',
        'reverse': True,
        'derive': None,
        'benchmark': 0.09,
        'type': 'float',
        'scale_factor': 1.0
    },
    {
        'name': 'Debt-to-EBITDA',
        'reverse': True,
        'derive': derive_debt_to_ebitda,
        'benchmark': None,
        'type': 'float',
        'scale_factor': 1.0
    },
    {
        'name': 'Interest Coverage',
        'reverse': False,
        'derive': None,
        'benchmark': 10.2,
        'type': 'float',
        'scale_factor': 1.0
    },
    {
        'name': 'Altman Z-Score',
        'reverse': False,
        'derive': None,
        'benchmark': 3.0,
        'type': 'float',
        'scale_factor': 1.0
    }
]


# benchmark values and reverse indicators here are for 3 year grow rates of the 
# underlying metrics.
_growth_metrics_inputs = [
    {
        'name': 'Revenue',
        'reverse': False,
        'derive': None,
        'benchmark': 0.1398,
        'type': 'percent',
        'scale_factor': 1.0
    },
    {
        'name': 'Operating Income',
        'reverse': False,
        'derive': None,
        'benchmark': 0.468,
        'type': 'percent',
        'scale_factor': 1.0
    },
    {
        'name': 'Net Income',
        'reverse': False,
        'derive': None,
        'benchmark': 0.7325,
        'type': 'percent',
        'scale_factor': 1.0
    },
    {
        'name': 'Cash Flow from Operations',
        'reverse': False,
        'derive': None,
        'benchmark': 0.1813,
        'type': 'percent',
        'scale_factor': 1.0
    },
]


_profitability_metrics_inputs = [
        {
            'name': 'Gross Margin %',
            'reverse': False,
            'derive': None,
            'benchmark': 0.3832,
            'type': 'percent',
            'scale_factor': 1/100
        },
        {
            'name': 'Operating Margin %',
            'reverse': False,
            'derive': None,
            'benchmark': 0.1456,
            'type': 'percent',
            'scale_factor': 1/100
        },
        {
            'name': 'Net Margin %',
            'reverse': False,
            'derive': None,
            'benchmark': 0.1046,
            'type': 'percent',
            'scale_factor': 1/100
        },
        {
            'name': 'FCF Margin %',
            'reverse': False,
            'derive': None,
            'benchmark': 0.1875,
            'type': 'percent',
            'scale_factor': 1/100
        },
        {
            'name': 'ROE %',
            'reverse': False,
            'derive': None,
            'benchmark': 0.196,
            'type': 'percent',
            'scale_factor': 1/100
        },
    ]


def get_fundamental_start_date(num_of_years=20, last_report_date=None):
    """
    This helper function gets the start date of the pre-specified history of 
    fundamentals.

    Inputs:
        'num_of_years': an integer, defaulted to be 20. It is the number of 
                        years to be considered in fundamentals related analysis.
        'last_report_date': a Python datetime object, defaulted to be None. It 
                            is the date of the last financial reports available 
                            in the history of fundamentals.
    """

    # set the last report date to utcnow if not given
    end_date = last_report_date if last_report_date else datetime.utcnow()
        
    # get the first year to be included, given the pre-specified time window
    start_year = end_date.year - num_of_years + 1

    return datetime(start_year, 1, 1)


def _get_average_rating(data_indicators, debug=False):
    """
    This helper function calculates the average rating of ratings included in 
    the input dictionary.

    It returns the average rating as a float number.

    Inputs:
        'data_indicators': a dictionary object. The 'value' should also be a 
                           dictionary object, with an attribute for 'Rating'.
        'debug': a boolean value, defaulted to False. When 'debug' is False, 
                 <value['Rating']> should contain a numeric value; if not, 
                 <value['Rating']['rating']> should contain a numeric value 
                 instead.
    """

    # initialize
    sum_of_ratings = 0.0
    num_of_ratings = 0

    # loop through all items in the input dictionary
    for key in data_indicators:
        rating = data_indicators[key]['Rating'] if not debug else \
            data_indicators[key]['Rating']['rating']

        # only accumulate values of rating when not None
        if rating is not None:
            sum_of_ratings += rating
            num_of_ratings += 1

    # return the average rating, and if there were no valid ratings, return None
    return sum_of_ratings / num_of_ratings if num_of_ratings > 0 else None


def get_fundamental_indicators(financials_history, 
                               start_date=datetime(1900, 1, 1),
                               financial_strength_name='Financial Strength',
                               growth_name='Business Growth',
                               profitability_name='Profitability',
                               debug=False):
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

    ######################
    # Financial strength #
    ######################

    data_indicators[financial_strength_name] = {}
    for item in _financial_strength_metrics_inputs:
        name = item['name']
        metric = get_metric(name=name, 
                            financials_history=financials_history, 
                            start_date=start_date,
                            scale_factor=item['scale_factor'],
                            derive=item['derive'])
        data_indicators[financial_strength_name][name] = \
            {
                'Object': metric,
                'Current': metric.TTM_value,
                'Type': item['type'],
                'Rating': metric.rating(benchmark_value=item['benchmark'], 
                                        reverse=item['reverse'],
                                        debug=debug)
            }
    
    # get the average rating
    data_indicators[financial_strength_name]['Average Rating'] = \
        _get_average_rating(
            data_indicators[financial_strength_name], debug=debug)

    ############
    #  Growth  #
    ############

    data_indicators[growth_name] = {}
    for item in _growth_metrics_inputs:
        name = item['name']
        metric = get_metric(name=name, 
                            financials_history=financials_history, 
                            start_date=start_date,
                            scale_factor=item['scale_factor'],
                            derive=item['derive'])
        growth_metric = metric.get_growth_metric()
        data_indicators[growth_name][growth_metric.name] = \
            {
                'Object': metric,
                'Current': float("{:.2f}".format(
                    metric.growth_rate(num_of_years=3))) \
                        if metric.growth_rate(num_of_years=3) else None,
                'Type': item['type'],
                'Rating': growth_metric.rating(
                    benchmark_value=item['benchmark'], reverse=item['reverse'], 
                    debug=debug, latest='Other')
            }

    # get the average rating
    data_indicators[growth_name]['Average Rating'] = \
        _get_average_rating(
            data_indicators[growth_name], debug=debug)

    #################
    # Profitability #
    #################

    data_indicators[profitability_name] = {}
    for item in _profitability_metrics_inputs:
        name = item['name']
        metric = get_metric(name=name, 
                            financials_history=financials_history, 
                            start_date=start_date,
                            scale_factor=item['scale_factor'],
                            derive=item['derive'])
        data_indicators[profitability_name][name] = \
            {
                'Object': metric,
                'Current': float("{:.2f}".format(metric.TTM_value)),
                'Type': item['type'],
                'Rating': metric.rating(benchmark_value=item['benchmark'], 
                                        reverse=item['reverse'],
                                        debug=debug)
            }
    # get the average rating
    data_indicators[profitability_name]['Average Rating'] = \
        _get_average_rating(
            data_indicators[profitability_name], debug=debug)

    # return the constructed dictionary
    return data_indicators


def get_estimated_return(quote_history_data, normal_price_data, 
                         dividend_yield=0):
    """
    This helper function calculate the estimated annualized return, given the 
    input quote history data and normal price data.

    The estimated annualized return is the sum of estimated annualized price 
    return/appreciation and the given dividend yield.

    Inputs:
        'quote_history_data': a dictionary of "<timestamp>: <price>", where 
                              timestamps are Python's datetime objects, and 
                              prices are those taken from historical quotes, 
                              including quotes from the latest month.
        'normal_price_data': a dictionary of "<timestamp>: <price>", where 
                             timestamps are Python's datetime objects, and 
                             prices are "normal prices" calculated based on 
                             some income/cash flow metric & the historical 
                             average price multiple based on the same metric.
                             It should include time periods where the "normal 
                             price" is based on analyst estimates, which is in 
                             the future.
        'dividend_yield': a numeric value, defaulted to be 0.
    """

    # get the historical price and the corresponding timestamp
    latest_quote_timestamp = max(quote_history_data.keys())
    latest_quote_price = quote_history_data[latest_quote_timestamp]

    # get the latest non-zero normal price and the corresponding timestamp
    normal_price_data_copy = normal_price_data.copy()
    while True:
        latest_normal_timestamp = max(normal_price_data_copy.keys())
        latest_normal_price = normal_price_data_copy[latest_normal_timestamp]
        if latest_normal_price != 0:
            break
        else:
            normal_price_data_copy.pop(latest_normal_timestamp)

    # compute and compute the estimated total annualized return, formatted
    num_of_years = (latest_normal_timestamp - latest_quote_timestamp).days / 365
    if num_of_years > 0:
        price_return = \
            (latest_normal_price / latest_quote_price)**(1/num_of_years) - 1
        return float("{:.2f}".format((price_return + dividend_yield) * 100))
    else:
        return None
