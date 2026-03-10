from flask import Blueprint

bp = Blueprint('eleitores', __name__)

from app.eleitores import routes  # noqa: F401, E402
