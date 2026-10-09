from collections import OrderedDict
from datetime import datetime, timedelta

from sqlalchemy import case, func

from .extensions import db
from .models import Order, Product, utcnow

RANGES = {"30d": 30, "90d": 90, "12m": 365}
DEFAULT_RANGE = "90d"


def parse_range(value):
    return value if value in RANGES else DEFAULT_RANGE


def _window(range_key, now):
    """Start on a bucket boundary so the first point is a full day, week or month."""
    end = now
    today = datetime(now.year, now.month, now.day)
    if range_key == "12m":
        month_index = now.year * 12 + (now.month - 1) - 11
        start = datetime(month_index // 12, month_index % 12 + 1, 1)
    elif range_key == "90d":
        this_monday = today - timedelta(days=today.weekday())
        start = this_monday - timedelta(weeks=12)
    else:
        start = today - timedelta(days=29)
    prev_start = start - (end - start)
    return start, end, prev_start


def _kpis(start, end):
    paid = case((Order.status == "paid", 1), else_=0)
    refunded = case((Order.status == "refunded", 1), else_=0)
    paid_revenue = case((Order.status == "paid", Order.total), else_=0)
    row = (
        db.session.query(
            func.count(Order.id),
            func.coalesce(func.sum(paid), 0),
            func.coalesce(func.sum(refunded), 0),
            func.coalesce(func.sum(paid_revenue), 0),
        )
        .filter(Order.created_at >= start, Order.created_at < end)
        .one()
    )
    orders, paid_count, refunded_count, revenue = row
    revenue = float(revenue or 0)
    settled = paid_count + refunded_count
    return {
        "revenue": round(revenue, 2),
        "orders": int(orders),
        "aov": round(revenue / paid_count, 2) if paid_count else 0.0,
        "refund_rate": round(100 * refunded_count / settled, 2) if settled else 0.0,
    }


def _covers_period(start, end):
    """True when stored history reaches back over (nearly) the whole comparison window."""
    earliest = db.session.query(func.min(Order.created_at)).scalar()
    if earliest is None:
        return False
    slack = (end - start) * 0.05
    return earliest <= start + slack


def _pct_change(current, previous):
    if not previous:
        return None
    return round(100 * (current - previous) / previous, 1)


def _bucket_key(dt, range_key):
    if range_key == "30d":
        return dt.strftime("%Y-%m-%d")
    if range_key == "90d":
        monday = dt - timedelta(days=dt.weekday())
        return monday.strftime("%Y-%m-%d")
    return dt.strftime("%Y-%m")


def _bucket_label(key, range_key):
    if range_key == "12m":
        return datetime.strptime(key, "%Y-%m").strftime("%b %Y")
    label = datetime.strptime(key, "%Y-%m-%d").strftime("%b %d")
    return f"Wk {label}" if range_key == "90d" else label


def _empty_buckets(start, end, range_key):
    buckets = OrderedDict()
    cursor = start
    step = timedelta(days=1)
    while cursor < end:
        buckets.setdefault(_bucket_key(cursor, range_key), 0.0)
        cursor += step
    return buckets


def _revenue_series(start, end, range_key):
    buckets = _empty_buckets(start, end, range_key)
    rows = (
        db.session.query(Order.created_at, Order.total)
        .filter(Order.status == "paid", Order.created_at >= start, Order.created_at < end)
        .all()
    )
    for created_at, total in rows:
        key = _bucket_key(created_at, range_key)
        if key in buckets:
            buckets[key] += float(total)
    return {
        "labels": [_bucket_label(k, range_key) for k in buckets],
        "values": [round(v, 2) for v in buckets.values()],
    }


def _top_products(start, end, limit=5):
    rows = (
        db.session.query(Product.name, func.sum(Order.total).label("revenue"))
        .join(Order, Order.product_id == Product.id)
        .filter(Order.status == "paid", Order.created_at >= start, Order.created_at < end)
        .group_by(Product.id)
        .order_by(func.sum(Order.total).desc())
        .limit(limit)
        .all()
    )
    return [{"name": name, "revenue": round(float(rev), 2)} for name, rev in rows]


def _by_region(start, end):
    rows = (
        db.session.query(Order.region, func.sum(Order.total))
        .filter(Order.status == "paid", Order.created_at >= start, Order.created_at < end)
        .group_by(Order.region)
        .order_by(func.sum(Order.total).desc())
        .all()
    )
    return [{"region": region, "revenue": round(float(rev), 2)} for region, rev in rows]


def dashboard_stats(range_key=DEFAULT_RANGE, now=None):
    range_key = parse_range(range_key)
    now = now or utcnow()
    start, end, prev_start = _window(range_key, now)
    current = _kpis(start, end)
    previous = _kpis(prev_start, start)
    has_previous = _covers_period(prev_start, start)
    changes = {
        key: (_pct_change(current[key], previous[key]) if has_previous else None)
        for key in current
    }
    return {
        "range": range_key,
        "start": start.isoformat(timespec="seconds"),
        "end": end.isoformat(timespec="seconds"),
        "kpis": current,
        "previous": previous if has_previous else None,
        "change_pct": changes,
        "revenue_series": _revenue_series(start, end, range_key),
        "top_products": _top_products(start, end),
        "by_region": _by_region(start, end),
    }
