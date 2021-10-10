from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.resources import CDN

def example_plot():
    """
    This function gives an example for plotting.
    """

    # create a simple Bokeh plot
    x = [1, 2, 3, 4, 5]
    y = [6, 7, 2, 4, 5]
    p = figure(title="Stock Price", x_axis_label='Time', y_axis_label='Price')
    p.line(x, y, legend_label='Price', line_width=2)

    payload = {}

    # get the javascript for loading BokehJS remotely from a CDN
    payload['resources'] = CDN.render()

    # get the HTML components to be rendered by BokehJS
    script, div = components(p)
    payload['script'] = script
    payload['div'] = div

    return payload
