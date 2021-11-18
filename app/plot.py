from datetime import datetime
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.resources import CDN
from bokeh.models import HoverTool
from app.metrics import Metric, TotalMetric

def example_plot():
    """
    This function gives an example for plotting.
    """

    # create a simple Bokeh plot
    x = [1, 2, 3, 4, 5]
    y = [6, 7, 2, 4, 5]
    p = figure(title="Stock Price", 
               x_axis_label='Time', 
               y_axis_label='Price',
               tools=[HoverTool()],
               tooltips="Data point @x has the value @y")
    p.line(x, y, legend_label='Price', line_width=2)

    payload = {}

    # get the javascript for loading BokehJS remotely from a CDN
    payload['resources'] = CDN.render()

    # get the HTML components to be rendered by BokehJS
    script, div = components(p)
    payload['script'] = script
    payload['div'] = div

    return payload


def _get_average_price_multiple(quote_history_data, metric_per_share_data):
    """
    This function calculates and returns the average price-to-metric ratio.
    
    Input:
        - "quote_history_data" - dictionary of "<timestamp>: <price>"
        - "metric_per_share_data" - dictionary of "<timestamp>: <per share 
                                    metric value>", with only one record per 
                                    year
    """
    
    # get the ending month of fiscal years, usually either Sep or Dec
    # this assumes the ending month is always the same across all fiscal years
    # TODO - can insert code here to check the assumption and raise an exception
    #        if the assumption does not hold for the input
    last_month_fiscal_years = list(metric_per_share_data.keys())[-1].month
    
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
        
        # initialize the interpolation flag to be False;
        interpolation_flag = False
        
        # when the current month is ealier than or the same as the last month 
        # of the fiscal year, use metric values of the current year and the 
        # previous year for interpolation
        if metric_value and metric_value_prev_year and \
            timestamp.month <= last_month_fiscal_years:

            # interpolate the monthly TTM value
            metric_value_interpolated = \
                metric_value_prev_year + \
                (metric_value - metric_value_prev_year) * \
                (timestamp.month + 12 - last_month_fiscal_years) / 12
            interpolation_flag = True
        
        # when the current month is greater than the last month of the fiscal 
        # year, use metric values of the current year and the next year for 
        # interpolation
        elif metric_value and metric_value_next_year and \
            timestamp.month > last_month_fiscal_years:
            
            # interpolate the monthly TTM value
            metric_value_interpolated = \
                metric_value + \
                (metric_value_next_year - metric_value) * \
                (timestamp.month - last_month_fiscal_years) / 12
            interpolation_flag = True
            
        # Only include the month in the calculation of average valuation ratios 
        # when the metric value of that month is positive - investors don't 
        # really look at P/X ratios when they are negative
        if interpolation_flag and metric_value_interpolated > 0:

            dict_timestamp_ratio[timestamp] = {
                'quote': quote_history_data[timestamp], 
                'metric': metric_value_interpolated, 
                'ratio': quote_history_data[timestamp] / \
                    metric_value_interpolated}
            
    # get all valuation ratios to a list, to prep for the calculation of the 
    # average ratio
    list_ratios = [dict_timestamp_ratio[timestamp]['ratio'] for timestamp in \
        dict_timestamp_ratio]

    # remove 12 highest ratios (1 year), and 12 lowest ratios
    for _ in range(12):
        list_ratios.remove(min(list_ratios))
        list_ratios.remove(max(list_ratios))
        
    return sum(list_ratios) / len(list_ratios)


def get_normal_price(metric_name, section_name, start_date, quote_history_data, 
                     financials_history, analyst_estimates):
    """
    This function returns normal prices with respect to the pre-specified 
    metric, based on the historical average price multiple of the same metric.
    """

    # convert the input start date to a datetime object
    # TODO - generalize this code later
    start_date_datetime_obj = datetime.strptime(start_date, '%m-%d-%Y')

    # get the sequence of historical shares outstanding (diluted average)
    num_of_shares = \
        Metric(name='Shares Outstanding (Diluted Average)',
               timestamps=financials_history['financials']['annuals']\
                   ['Fiscal Year'],
               values=financials_history['financials']['annuals']\
                   ['income_statement']['Shares Outstanding (Diluted Average)'],
               start_date=start_date_datetime_obj)

    # get the sequence of historical values of the pre-specified metric, with
    # number of shares set
    metric = TotalMetric(name=metric_name, 
                         timestamps=financials_history['financials']['annuals']\
                             ['Fiscal Year'],
                         values=financials_history['financials']['annuals']\
                             [section_name][metric_name],
                         start_date=start_date_datetime_obj)

    metric.num_of_shares = num_of_shares.values

    # calculate the historical average price multiple
    average_price_multiple = \
        _get_average_price_multiple(quote_history_data=quote_history_data,
                                    metric_per_share_data=metric.per_share_data)

    # get the per share data of analyst estimates
    field_lookup = {
        'EBIT': {
            'field_name': 'ebit_estimate',
            'per_share': False
        },
        'EBITDA': {
            'field_name': 'ebitda_estimate',
            'per_share': False
        },
        'Net Income': {
            'field_name': 'per_share_eps_estimate',
            'per_share': True
        }
    }

    if field_lookup[metric_name]['per_share']:
        metric_estimated = \
            Metric(name=metric_name + ' (estimated)',
                   timestamps=analyst_estimates['annual']['date'],
                   values=analyst_estimates['annual'][\
                        field_lookup[metric_name]['field_name']],
                   start_date=start_date_datetime_obj,
                   input_timestamps_format='%Y%m')
        metric_estimated_per_share_data = metric_estimated.data
    else:
        metric_estimated = \
            TotalMetric(name=metric_name + ' (estimated)',
                        timestamps=analyst_estimates['annual']['date'],
                        values=analyst_estimates['annual'][\
                            field_lookup[metric_name]['field_name']],
                        start_date=start_date_datetime_obj,
                        input_timestamps_format='%Y%m')
        metric_estimated.num_of_shares = [num_of_shares.TTM_value]
        metric_estimated_per_share_data = metric_estimated.per_share_data

    # calculate the normal prices with respect to historical values as well as 
    # the analyst estimated values of the pre-specified metric
    metric_combined_per_share_data = \
        {**metric.per_share_data, **metric_estimated_per_share_data}

    return average_price_multiple, {timestamp: max(0, average_price_multiple * \
        metric_combined_per_share_data[timestamp]) for timestamp in \
        metric_combined_per_share_data}


def stock_valuation_plot(quote_history_data, normal_price_data, 
                         average_price_multiple):
    """
    This function sets up the payload needed for BokehJS to render 
    a "price" vs "normal price" plot against timestamps.
    """

    # set up tooltips & formats
    hover_tool = HoverTool(
        tooltips = [
            ('Date',  '@x{%F}'),
            ('Close', '$@y{%0.2f}')
        ],
        formatters = {
            '@x' : 'datetime',
            '@y' : 'printf'
        }
    )

    # initiate a Bokeh figure object
    p = figure(title="Price Correlated with Fundamentals",
               x_axis_type='datetime',
               x_axis_label='Time',
               y_axis_label='Price',
               tools=[hover_tool])

    # add a line for quote history
    p.line(list(quote_history_data.keys()),
           list(quote_history_data.values()),
           legend_label='Stock Price',
           color='black',
           line_width=2)

    # add a line for "normal prices" by year
    p.line(list(normal_price_data.keys()),
           list(normal_price_data.values()),
           legend_label = 'Normal Price (Ratio {:5.2f})'.format(
               average_price_multiple),
           line_width = 2)

    # customizations
    p.title.align = 'center'
    p.title.text_color = 'orange'
    p.title.text_font_size = '25px'
    p.legend.location = 'top_left'

    # get the javascript for loading BokehJS remotely from a CDN
    payload = {}
    payload['resources'] = CDN.render()

    # get the HTML components to be rendered by BokehJS
    script, div = components(p)
    payload['script'] = script
    payload['div'] = div

    return payload
