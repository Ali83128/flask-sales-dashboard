from sqlalchemy import or_

from .models import REGIONS, STATUSES, Customer, Order


def order_filters_from(args):
    return {
        "q": (args.get("q") or "").strip()[:80],
        "status": args.get("status") if args.get("status") in STATUSES else "",
        "region": args.get("region") if args.get("region") in REGIONS else "",
    }


def filtered_orders_query(filters):
    query = Order.query.join(Customer)
    if filters["q"]:
        like = f"%{filters['q']}%"
        query = query.filter(
            or_(Order.number.ilike(like), Customer.name.ilike(like), Customer.email.ilike(like))
        )
    if filters["status"]:
        query = query.filter(Order.status == filters["status"])
    if filters["region"]:
        query = query.filter(Order.region == filters["region"])
    return query.order_by(Order.created_at.desc())
