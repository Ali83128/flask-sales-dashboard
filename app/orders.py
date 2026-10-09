import csv
import io
from flask import Blueprint, Response, current_app, render_template, request

from .filters import filtered_orders_query, order_filters_from
from .models import REGIONS, STATUSES, utcnow
from .security import login_required

bp = Blueprint("orders", __name__, url_prefix="/orders")

CSV_FIELDS = ["number", "created_at", "customer", "email", "product", "sku",
              "quantity", "unit_price", "total", "status", "region"]


@bp.route("/")
@login_required
def index():
    filters = order_filters_from(request.args)
    page = request.args.get("page", 1, type=int)
    pagination = filtered_orders_query(filters).paginate(
        page=page, per_page=current_app.config["ORDERS_PER_PAGE"], error_out=False
    )
    return render_template(
        "orders.html", pagination=pagination, filters=filters, regions=REGIONS, statuses=STATUSES
    )


@bp.route("/export.csv")
@login_required
def export_csv():
    filters = order_filters_from(request.args)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDS)
    writer.writeheader()
    for order in filtered_orders_query(filters).yield_per(500):
        writer.writerow(order.to_dict())
    stamp = utcnow().strftime("%Y%m%d")
    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=orders-{stamp}.csv"},
    )
