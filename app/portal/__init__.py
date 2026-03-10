from flask import Blueprint

bp = Blueprint('portal', __name__)

from app.portal import routes  # noqa: F401, E402
