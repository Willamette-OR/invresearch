from flask import render_template
from app import app


@app.route('/')
@app.route('/index')
def index():
    """This function implements the view logic for the index page."""

    return render_template('index.html', title='Home')
