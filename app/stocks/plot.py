import itertools
from datetime import datetime
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.resources import CDN
from bokeh.models import HoverTool
from bokeh.palettes import Dark2_5 as palette
from app.metrics import Metric, TotalMetric
from app.fundamental_analysis import get_valuation_ratios

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


def _get_average_price_multiple(quote_history_data, metric_per_share_data, \
    min_num_of_ratios = 36):
    """
    This function calculates and returns the average price-to-metric ratio.
    
    Input:
        - "quote_history_data" - dictionary of "<timestamp>: <price>"
        - "metric_per_share_data" - dictionary of "<timestamp>: <per share 
                                    metric value>", with only one record per 
                                    year
        - 'min_num_of_ratios' - minimum number of ratios needed to calculate the
                                average valuation ratios, before removing 
                                outliers
    """

    # get a dictionary of { <timestamp>: {<"ratio">: <price multiple>, ...} }
    dict_timestamp_ratio = get_valuation_ratios(
        quote_history_data=quote_history_data, 
        metric_per_share_data=metric_per_share_data
        )
            
    # get all valuation ratios to a list, to prep for the calculation of the 
    # average ratio
    list_ratios = [dict_timestamp_ratio[timestamp]['ratio'] for timestamp in \
        dict_timestamp_ratio]

    # discard valualtion ratio calculations if the total number of valid \
    # ratios is too little
    if len(list_ratios) < min_num_of_ratios:
        return None

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
    # return special values if the average price multiple calculations did not 
    # return valid values
    if not average_price_multiple:
        return None, {}, None

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
        metric_combined_per_share_data}, metric_combined_per_share_data


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
            ('Price', '$@y{%0.2f}')
        ],
        formatters = {
            '@x' : 'datetime',
            '@y' : 'printf'
        }
    )

    # initiate a Bokeh figure object
    p = figure(width=650,
               height=400,
               x_axis_type='datetime',
               x_axis_label='Time',
               y_axis_label='Price',
               tools=[hover_tool])

    # deactivate the Bokeh toolbar
    p.toolbar_location = None

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

    # add markers on top of the line for "normal prices"
    p.dot(list(normal_price_data.keys()),
          list(normal_price_data.values()),
          size=25)
    
    # shade the area under the line for "normal prices"
    p.varea(
        x=list(normal_price_data.keys()),
        y1=0,
        y2=list(normal_price_data.values()),
        alpha=0.2
    )

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


def get_valplot_dates(quote_history, financials_history, num_of_years=20):
    """
    This function calculates and returns dates needed to filter the quote 
    history and the financials history for stock valuation plotting, as well as 
    the total number of years that can possibly be used for plotting. 

    if the total # of overlapping years, N, between the input quote history data 
    and the input financials history, is less than the input num_of_years, M, 
    then dates needed for valuation plotting will be based off the number N. 
    Otherwise dates will be based off the number M.

    Inputs:
        'quote_history': a dictionary object, and each item in it looks like 
                         "<timestamp>: <price>".
        'financials_history': a dictionary object, which for now holds the 
                              payload data returned by the GuruFocus API for 
                              historical financials .
        'num_of_years': # of years of quote history intended to be included in 
                        valuation plotting. But the actual # of years available 
                        for valuation plotting might be less than this number.
    """

    # get the earliest and latest dates in the quote history data
    earliest_date_quote = min(quote_history.keys())
    latest_date_quote = max(quote_history.keys())

    # get the earliest and latest dates in the financial history data

    # in order to properly preprocess the payload data returned by the 
    # financials API, create a metric object using the payload, and then get 
    # the timestamps from the metric object
    num_of_shares = \
        Metric(name='Shares Outstanding (Diluted Average)',
               timestamps=financials_history['financials']['annuals']\
                   ['Fiscal Year'],
               values=financials_history['financials']['annuals']\
                   ['income_statement']['Shares Outstanding (Diluted Average)'],
               start_date=datetime(1900, 1, 1))
    earliest_date_financials = min(num_of_shares.timestamps)
    latest_date_financials = max(num_of_shares.timestamps)

    # get the maximum number of years of overlap between the quote and the 
    # financials history data, which is an integer and the floor of the years 
    # delta 
    earliest_date_overlap = max(earliest_date_financials, earliest_date_quote)
    latest_date_overlap = min(latest_date_financials, latest_date_quote)
    max_years_overlap = int(
        (latest_date_overlap - earliest_date_overlap).days / 365.2425)

    # set the end date to utcnow, in the format of '%m-%d-%Y'
    now = datetime.utcnow()
    end_date = now.strftime('%m-%d-%Y')

    # set the start date of quote history
    if max_years_overlap < num_of_years:
        start_year = earliest_date_quote.year
        start_date_quote_history = earliest_date_overlap.strftime('%m-%d-%Y')
    else:
        start_year = latest_date_overlap.year - num_of_years
        start_date_quote_history = '01-01-{}'.format(start_year)

    # set the start date of financials history to be a year ahead of that of 
    # quote history;
    # 1 more year of financials history is needed for earnings/cash flow 
    # interpolations when computing average price multiples
    start_date_financials_history = '01-01-{}'.format(start_year - 1)

    return start_date_quote_history, start_date_financials_history, end_date, \
           max_years_overlap


def get_durations(quote_history, financials_history, min_years=3, max_years=20):
    """
    This function returns a list of acceptable durations for stock valuation 
    plotting.

    Each acceptable duration refers to a value for # of years of financials 
    history & quote history to be used together in calculating the historical 
    average price multiple.

    As an example, if 3 years is an "acceptible time window", it implies a 3.x 
    years overlap of the quote history data and financials history data is 
    available to used for the calculation of average price multiple of that 
    same time window.

    Inputs:
        'quote_history': a dictionary object, and each item in it looks like 
                         "<timestamp>: <price>".
        'financials_history': a dictionary object, which for now holds the 
                              payload data returned by the GuruFocus API for 
                              historical financials .
        'min_years': an integer defaulted to be 3, the minimum number of years 
                     allowed for the average price multiple calculation.
        'max_years': an integer defaulted to be 20, the maximum number of years 
                     allowed for the average price multiple calculation.
    """

    # get the total number of years that can possibly be used for valuation 
    # plotting, based on the input quote history and the input financials 
    # history data
    _, _, _, max_years_overlap = get_valplot_dates(
        quote_history=quote_history, financials_history=financials_history)   

    # get the maximum number of years allowed for average price multiple 
    # calculation, which is the lesser of the two below:
    #   (1) the max # years overlap between the quote and the financials history
    #   (2) the max # years allowed passed as an input
    max_duration = min(max_years_overlap, max_years)

    # return None if the maximum number of years allowed derived above is less 
    # than the minimum number of years allowed passed as an input
    if max_duration < min_years:
        return None

    # return all allowed durations (in years) in a list
    return [(value + 1) for value in \
            range(max_duration) if (value + 1) >= min_years]


def timeseries_plot(name, data_list, symbols, 
                    start_date=datetime(1900, 1, 1)):
    """
    This function constructs a time-series plot for data included in the input 
    list, for timestamps after the given start date.
    It returns a payload for rendering, as well as the first data object in the 
    input sequence.

    Inputs:
        'name': a string object, and the name of the metric/data to be plotted.
        'data_list': a sequence of dictionary objects, where each dictionary 
                     consists of pairs of <'timestamp': value>.
        'symbols': a sequence of symbols, where each symbol corresponds to 
                   the dictionary object in the same location from 'data_list'.
        'start_date': a Python datetime object. Only data after this date will 
                      be used for plotting.
    """

    # validate inputs
    if len(data_list) != len(symbols):
        raise ValueError('The lengths of data_list and symbols must be equal.')

    # set up tooltips & formats
    hover_tool = HoverTool(
        tooltips = [
            ('Date',  '@x{%F}'),
            ('Value', '@y{%0.2f}')
        ],
        formatters = {
            '@x' : 'datetime',
            '@y' : 'printf'
        }
    )

    # initiate a Bokeh figure object
    p = figure(x_axis_type='datetime',
               x_axis_label='Time',
               y_axis_label='Value',
               tools=[hover_tool])

    # creates a color iterator
    colors = itertools.cycle(palette)

    # add a line for each set of data in the input list
    for i, color in zip(range(len(data_list)), colors):
        data = {
            timestamp: data_list[i][timestamp] for timestamp in data_list[i] 
            if timestamp >= start_date
        }

        # save the first data object for output
        if i == 0:
            output_data = data

        # add a line for quote history
        p.line(list(data.keys()),
               list(data.values()),
               legend_label=symbols[i] + ': ' + name,
               color=color,
               line_width=2)

        # add markers on top of the line
        p.dot(list(data.keys()), list(data.values()), size=25, color=color)

    # customizations
    p.toolbar_location = None
    p.legend.location = 'top_left'
    p.sizing_mode = 'scale_width'
    p.plot_height = 200

    # get the javascript for loading BokehJS remotely from a CDN
    payload = {}
    payload['resources'] = CDN.render()

    # get the HTML components to be rendered by BokehJS
    script, div = components(p)
    payload['script'] = script
    payload['div'] = div

    return payload, output_data
