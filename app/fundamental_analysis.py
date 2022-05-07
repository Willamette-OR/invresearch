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
    'ROE %': 'common_size_ratios',
    'PE Ratio': 'valuation_ratios',
    'PB Ratio': 'valuation_ratios',
    'Price-to-Free-Cash-Flow': 'valuation_ratios',
    'Price-to-Operating-Cash-Flow': 'valuation_ratios',
    'PS Ratio': 'valuation_ratios',
    'Earnings per Share (Diluted)': 'per_share_data_array',
    'Book Value per Share': 'per_share_data_array',
    'Free Cash Flow per Share': 'per_share_data_array',
    'Operating Cash Flow per Share': 'per_share_data_array',
    'Revenue per Share': 'per_share_data_array',
    'Shares Outstanding (Diluted Average)': 'income_statement',
    'Dividends per Share': 'per_share_data_array',
    'Dividend Payout Ratio': 'common_size_ratios',
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


def get_valuation_ratios(quote_history_data, metric_per_share_data, 
                         get_latest_ratios=False, only_positives=True):
    """
    This function calculates and returns a dictionary of 
    {<timestamp>: <price multiple} for all timestamps where possible based on 
    the input quote history data and the input metric (per share) data.
    
    Input:
        - "quote_history_data" - dictionary of "<timestamp>: <price>"
        - "metric_per_share_data" - dictionary of "<timestamp>: <per share 
                                    metric value>", with only one record per 
                                    year
        - "get_latest_ratios" - a boolean value, defaulted to be False. When 
                                True, valuation ratios for quotes even 
                                after the most recent month included in the 
                                input financial history data will still be 
                                calculated. 
        - "only_positives" - a boolean value, defaulted to be True. If True, 
                             only positive ratios will be kept. 
    """
    
    # get the ending month of fiscal years, usually either Sep or Dec
    # this assumes the ending month is always the same across all fiscal years
    # TODO - can insert code here to check the assumption and raise an exception
    #        if the assumption does not hold for the input
    metric_data_last_timestamp = list(metric_per_share_data.keys())[-1]
    last_month_fiscal_years = metric_data_last_timestamp.month
    
    # create a new dictionary of <fiscal year>: <per share metric value> for 
    # easy per share metric value look up by fiscal year
    list_years = [timestamp.year for timestamp in metric_per_share_data]
    dict_year_metric = dict(zip(list_years, metric_per_share_data.values()))

    # form a new dict of "<timestamp>: {'quote': <quote>, 'metric': <metric>, 
    # 'ratio': <ratio>}"
    dict_timestamp_ratio = {}
    for timestamp in quote_history_data:
        
        # get the annual values for the current year, the prev year and the 
        # next year
        metric_value = dict_year_metric.get(timestamp.year)
        metric_value_prev_year = dict_year_metric.get(timestamp.year - 1)
        metric_value_next_year = dict_year_metric.get(timestamp.year + 1)
        
        # initialize/reset the variable that holds the interpolated / 
        # extrapolated value for the metric;
        metric_value_derived = None
        
        # when the current month is ealier than or the same as the last month 
        # of the fiscal year, use metric values of the current year and the 
        # previous year for interpolation
        if metric_value and metric_value_prev_year and \
            timestamp.month <= last_month_fiscal_years:

            # interpolate the monthly TTM value
            metric_value_derived = \
                metric_value_prev_year + \
                (metric_value - metric_value_prev_year) * \
                (timestamp.month + 12 - last_month_fiscal_years) / 12
        
        # when the current month is greater than the last month of the fiscal 
        # year, use metric values of the current year and the next year for 
        # interpolation
        elif metric_value and metric_value_next_year and \
            timestamp.month > last_month_fiscal_years:
            
            # interpolate the monthly TTM value
            metric_value_derived = \
                metric_value + \
                (metric_value_next_year - metric_value) * \
                (timestamp.month - last_month_fiscal_years) / 12

        # when the current month is greater than the most recent month included 
        # in the input financial history data, use just the metric value of the 
        # current year
        elif get_latest_ratios and timestamp > metric_data_last_timestamp:
            metric_value_derived = metric_value if metric_value is not None \
                                                else metric_value_prev_year
            
        # only keep records with positive interpolated/extrapolated metric 
        # values at zero - investors don't really consider P/X ratios when they 
        # are negative
        if metric_value_derived is not None:

            if only_positives:
                if metric_value_derived > 0:
                    dict_timestamp_ratio[timestamp] = {
                        'quote': quote_history_data[timestamp], 
                        'metric': metric_value_derived, 
                        'ratio': quote_history_data[timestamp] / 
                                 metric_value_derived}
            else:
                dict_timestamp_ratio[timestamp] = {
                        'quote': quote_history_data[timestamp], 
                        'metric': metric_value_derived, 
                        'ratio': quote_history_data[timestamp] / 
                                 metric_value_derived 
                                 if metric_value_derived != 0 else 0}

    return dict_timestamp_ratio


def derive_valuation_ratios(name, underlying_metric_name, financials_history, 
                            quote_history_data, start_date):
    """
    This function returns a metric that captures the history of price multiple 
    of a given underlying financial metric.

    Inputs:
        "name": a string value, name of the output metric object to be returned
        "underlying_metric_name": name of the underlying metric for the price
                                  multiple, which can be used to look up for the
                                  values in the input financials history payload
        "financials_history": the input data payload of financials history
        "quote_history": the input data payload of quote history
        "start_date": a Python datetime object, the start date of a time window;
                      only valuation ratios/price multiples for dates within 
                      that time window will be included in the metric object to 
                      be returned 
    """

    # get the underlying metric from the input financials history payload
    underlying_metric = get_metric(
        name=underlying_metric_name, 
        financials_history=financials_history, 
        start_date=start_date
        )

    # get the dictionary of <timestamp>: {<"ratio">: <price multiple>, ...}
    dict_timestamp_ratio = get_valuation_ratios(
        quote_history_data=quote_history_data, 
        metric_per_share_data=underlying_metric.data,
        get_latest_ratios=True,
        only_positives=False
        )

    # create a new metric for this valuation ratio / price multiple data
    ratios = [dict_timestamp_ratio[timestamp]['ratio'] 
              for timestamp in dict_timestamp_ratio]
    
    # save the valuation ratios in a Metric object
    valuation_ratio = Metric(
        name=name, 
        timestamps=list(dict_timestamp_ratio.keys()), 
        values=ratios, 
        start_date=start_date, 
        input_timestamps_format=None
        )
    valuation_ratio.TTM_value = valuation_ratio.values[-1]
    
    return valuation_ratio


def get_metric(name, financials_history, start_date, convert_to_numeric=True, 
               scale_factor=1.0, derive=None, quote_history_data=None, 
               underlying_metric_name=None):
    """
    This helper function extracts a metric's data from the financials history 
    data, based on the given metric name and start date of the financials 
    history to be considered.
    """

    # if 'derive' function is given, derive the metric first
    if derive:
        if not quote_history_data:
            return derive(name, financials_history, start_date)
        else:
            return derive(name, underlying_metric_name, financials_history, 
                          quote_history_data, start_date)
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
        if name == 'Cash, Cash Equivalents, Marketable Securities' \
            and values is None:
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


# benchmark values and reverse indicators here are for financial strength 
# metrics
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
    },
    {
        'name': 'Shares Outstanding (Diluted Average)',
        'reverse': True,
        'derive': None,
        'benchmark': None,
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


# benchmark values and reverse indicators here are for profitability metrics.
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


# benchmark values and reverse indicators here are for valuation metrics.
_valuation_metrics_inputs = [
        {
            'name': 'PE Ratio',
            'underlying-metric': 'Earnings per Share (Diluted)',
            'reverse': True,
            'derive': derive_valuation_ratios,
            'benchmark': None,
            'type': 'float',
            'scale_factor': 1.0
        },
        {
            'name': 'PB Ratio',
            'underlying-metric': 'Book Value per Share',
            'reverse': True,
            'derive': derive_valuation_ratios,
            'benchmark': None,
            'type': 'float',
            'scale_factor': 1.0
        },
        {
            'name': 'Price-to-Free-Cash-Flow',
            'underlying-metric': 'Free Cash Flow per Share',
            'reverse': True,
            'derive': derive_valuation_ratios,
            'benchmark': None,
            'type': 'float',
            'scale_factor': 1.0
        },
        {
            'name': 'Price-to-Operating-Cash-Flow',
            'underlying-metric': 'Operating Cash Flow per Share',
            'reverse': True,
            'derive': derive_valuation_ratios,
            'benchmark': None,
            'type': 'float',
            'scale_factor': 1.0
        },
        {
            'name': 'PS Ratio',
            'underlying-metric': 'Revenue per Share',
            'reverse': True,
            'derive': derive_valuation_ratios,
            'benchmark': None,
            'type': 'float',
            'scale_factor': 1.0
        },
    ]

# benchmark values and reverse indicators here are for valuation metrics.
_dividend_metrics_inputs = [
        {
            'name': 'Dividends per Share',
            'reverse': False,
            'derive': None,
            'benchmark': None,
            'type': 'float',
            'scale_factor': 1.0
        },
        {
            'name': 'Dividend Payout Ratio',
            'reverse': True,
            'derive': None,
            'benchmark': None,
            'type': 'float',
            'scale_factor': 1.0
        }
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
                               quote_history_data,
                               start_date=datetime(1900, 1, 1),
                               financial_strength_name='Financial Strength',
                               growth_name='Business Growth',
                               profitability_name='Profitability',
                               valuation_name='Stock Valuation',
                               dividend_name='Dividend Growth',
                               debug=False):
    """
    This function gets raw data from the input financials history data after a 
    pre-specified start date,creates and returns a dictionary of indicators 
    needed for stocks' fundamental analysis.

    Inputs:
        'financials_history': data of a stock's financials history
        'quote_history_data': data of a stock's quote history
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

    ################
    #   Valuation  #
    # ##############

    data_indicators[valuation_name] = {}
    for item in _valuation_metrics_inputs:
        name = item['name']
        metric = get_metric(name=name, 
                            underlying_metric_name=item['underlying-metric'],
                            financials_history=financials_history, 
                            quote_history_data=quote_history_data,
                            start_date=start_date,
                            scale_factor=item['scale_factor'],
                            derive=item['derive'])
        data_indicators[valuation_name][name] = \
            {
                'Object': metric,
                'Current': metric.TTM_value,
                'Type': item['type'],
                'Rating': metric.rating(benchmark_value=item['benchmark'], 
                                        reverse=item['reverse'],
                                        debug=debug,
                                        trend_threshold_value=None)
            }
    
    # get the average rating
    data_indicators[valuation_name]['Average Rating'] = \
        _get_average_rating(
            data_indicators[valuation_name], debug=debug) 

    ###################
    # Dividend Growth #
    ###################

    data_indicators[dividend_name] = {}
    for item in _dividend_metrics_inputs:
        name = item['name']
        metric = get_metric(name=name, 
                            financials_history=financials_history, 
                            start_date=start_date,
                            scale_factor=item['scale_factor'],
                            derive=item['derive'])
        data_indicators[dividend_name][name] = \
            {
                'Object': metric,
                'Current': float("{:.2f}".format(metric.TTM_value)),
                'Type': item['type'],
                'Rating': metric.rating(benchmark_value=item['benchmark'], 
                                        reverse=item['reverse'],
                                        debug=debug)
            }
    # get the average rating
    data_indicators[dividend_name]['Average Rating'] = \
        _get_average_rating(
            data_indicators[dividend_name], debug=debug)

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
