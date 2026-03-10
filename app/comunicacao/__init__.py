from flask import Blueprint

bp = Blueprint('comunicacao', __name__)

from app.comunicacao import routes  # noqa: F401, E402
