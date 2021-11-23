from flask import Blueprint

bp = Blueprint('stocks', __name__)

from app.stocks import routes
