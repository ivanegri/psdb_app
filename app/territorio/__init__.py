from flask import Blueprint

bp = Blueprint('territorio', __name__)

from app.territorio import routes  # noqa: F401, E402
