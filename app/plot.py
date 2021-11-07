from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.resources import CDN
from bokeh.models import HoverTool, formatters

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


def stock_valuation_plot(quote_history_data):
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

    # get the javascript for loading BokehJS remotely from a CDN
    payload = {}
    payload['resources'] = CDN.render()

    # get the HTML components to be rendered by BokehJS
    script, div = components(p)
    payload['script'] = script
    payload['div'] = div

    return payload
