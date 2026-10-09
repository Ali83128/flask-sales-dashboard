from flask import Blueprint, jsonify, request

from .filters import filtered_orders_query, order_filters_from
from .security import login_required
from .stats import dashboard_stats, parse_range

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/stats")
@login_required
def stats():
    return jsonify(dashboard_stats(parse_range(request.args.get("range"))))


@bp.route("/orders")
@login_required
def orders():
    filters = order_filters_from(request.args)
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 50, type=int), 1), 200)
    pagination = filtered_orders_query(filters).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify(
        {
            "filters": filters,
            "page": pagination.page,
            "per_page": per_page,
            "total": pagination.total,
            "pages": pagination.pages,
            "items": [o.to_dict() for o in pagination.items],
        }
    )
