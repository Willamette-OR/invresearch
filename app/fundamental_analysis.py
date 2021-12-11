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


def get_metric(name, financials_history, start_date, convert_to_numeric=True):
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
        start_date=start_date,
        convert_to_numeric=convert_to_numeric
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

    ######################
    # Financial strength #
    ######################

    data_indicators['financial strength'] = {}

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
    data_indicators['financial strength'][_name] = \
        float("{:.2f}".format(_metric.TTM_value))

    # Equity-to-Asset
    # save the TTM value
    _name = 'Equity-to-Asset'
    _metric = get_metric(name=_name, financials_history=financials_history, 
                         start_date=start_date)
    data_indicators['financial strength'][_name] = \
        float("{:.2f}".format(_metric.TTM_value))

    # Debt-to-Equity
    # save the TTM value
    _name = 'Debt-to-Equity'
    _metric = get_metric(name=_name, financials_history=financials_history,
                         start_date=start_date)
    data_indicators['financial strength'][_name] = \
        "{:.2f}".format(_metric.TTM_value)

    # Debt-to-EBITDA
    # save the TTM value
    _name = 'Debt-to-EBITDA'
    ebitda = get_metric(name='EBITDA', financials_history=financials_history, 
                        start_date=start_date)
    _metric = (short_term_debt + long_term_debt) / ebitda
    data_indicators['financial strength'][_name] = \
        float("{:.2f}".format(_metric.TTM_value))

    # Interest Coverage
    # save the TTM value
    _name = 'Interest Coverage'
    _metric = get_metric(name=_name, financials_history=financials_history,
                         start_date=start_date, convert_to_numeric=False)
    data_indicators['financial strength'][_name] = _metric.TTM_value \
        if _metric.TTM_value != '0' else 'No Debt'

    # Altman Z-Score
    # save the TTM value
    _name = 'Altman Z-Score'
    _metric = get_metric(name=_name, financials_history=financials_history,
                         start_date=start_date)
    data_indicators['financial strength'][_name] = \
        float("{:.2f}".format(_metric.TTM_value))

    ############
    #  Growth  #
    ############

    data_indicators['growth'] = {}

    # 3-Year & 5-Year Revenue Growth Rate
    revenue = get_metric(name='Revenue', financials_history=financials_history, 
                         start_date=start_date)
    data_indicators['growth']['3-Year Revenue Growth Rate'] = \
        "{:.2f}%".format(revenue.growth_rate(num_of_years=3) * 100) \
            if revenue.growth_rate(num_of_years=3) else 'N/A'
    data_indicators['growth']['5-Year Revenue Growth Rate'] = \
        "{:.2f}%".format(revenue.growth_rate(num_of_years=5) * 100) \
            if revenue.growth_rate(num_of_years=5) else 'N/A'

    # 3-Year & 5-Year Operating Income Growth Rate
    _name = 'Operating Income'
    operating_income = get_metric(name=_name, 
                                  financials_history=financials_history, 
                                  start_date=start_date)
    data_indicators['growth']['3-Year Operating Income Growth Rate'] = \
        "{:.2f}%".format(operating_income.growth_rate(num_of_years=3) * 100) \
            if operating_income.growth_rate(num_of_years=3) else 'N/A'
    data_indicators['growth']['5-Year Operating Income Growth Rate'] = \
        "{:.2f}%".format(operating_income.growth_rate(num_of_years=5) * 100) \
            if operating_income.growth_rate(num_of_years=5) else 'N/A'

    # 3-Year & 5-Year Net Income Growth Rate 
    _name = 'Net Income'
    net_income = get_metric(name=_name, financials_history=financials_history, 
                            start_date=start_date)
    data_indicators['growth']['3-Year Net Income Growth Rate'] = \
        "{:.2f}%".format(net_income.growth_rate(num_of_years=3) * 100) \
            if net_income.growth_rate(num_of_years=3) else "N/A"
    data_indicators['growth']['5-Year Net Income Growth Rate'] = \
        "{:.2f}%".format(net_income.growth_rate(num_of_years=5) * 100) \
            if net_income.growth_rate(num_of_years=5) else "N/A"

    # 3-Year & 5-Year Operating Cash Flow Growth Rate
    _name = 'Cash Flow from Operations'
    operating_cashflow = get_metric(name=_name, 
                                    financials_history=financials_history, 
                                    start_date=start_date)
    data_indicators['growth']['3-Year Operating Cash Flow Growth Rate'] = \
        "{:.2f}%".format(operating_cashflow.growth_rate(num_of_years=3) * 100) \
            if operating_cashflow.growth_rate(num_of_years=3) else "N/A"
    data_indicators['growth']['5-Year Operating Cash Flow Growth Rate'] = \
        "{:.2f}%".format(operating_cashflow.growth_rate(num_of_years=5) * 100) \
            if operating_cashflow.growth_rate(num_of_years=5) else "N/A"

    #################
    # Profitability #
    #################

    data_indicators['profitability'] = {}

    # Gross Margin
    _name = 'Gross Margin %'
    gross_margin = get_metric(name=_name, 
                              financials_history=financials_history, 
                              start_date=start_date)
    data_indicators['profitability'][_name] = \
        "{:.2f}%".format(gross_margin.TTM_value)

    # Operating Margin
    _name = 'Operating Margin %'
    operating_margin = get_metric(name=_name, 
                                  financials_history=financials_history, 
                                  start_date=start_date)
    data_indicators['profitability'][_name] = \
        "{:.2f}%".format(operating_margin.TTM_value)

    # Net Margin
    _name = 'Net Margin %'
    net_margin = get_metric(name=_name, 
                            financials_history=financials_history, 
                            start_date=start_date)
    data_indicators['profitability'][_name] = \
        "{:.2f}%".format(net_margin.TTM_value)
    
    # FCF Margin
    _name = 'FCF Margin %'
    fcf_margin = get_metric(name=_name, financials_history=financials_history, 
                            start_date=start_date)
    data_indicators['profitability'][_name] = \
        "{:.2f}%".format(fcf_margin.TTM_value)

    # ROE
    _name = 'ROE %'
    roe = get_metric(name=_name, financials_history=financials_history, 
                     start_date=start_date)
    data_indicators['profitability'][_name] = "{:.2f}%".format(roe.TTM_value)

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
