from app import app


@app.route('/')
@app.route('/index')
def index():
    """This function implements the view logic for the index page."""

    return "Hello world!"
