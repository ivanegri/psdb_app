from flask import Blueprint

bp = Blueprint('acoes', __name__)

from app.acoes import routes  # noqa: F401, E402
