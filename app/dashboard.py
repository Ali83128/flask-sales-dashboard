from flask import Blueprint, render_template, request

from .security import login_required
from .stats import RANGES, dashboard_stats, parse_range

bp = Blueprint("dashboard", __name__)


@bp.route("/")
@login_required
def index():
    range_key = parse_range(request.args.get("range"))
    stats = dashboard_stats(range_key)
    return render_template("dashboard.html", stats=stats, ranges=RANGES, active_range=range_key)
