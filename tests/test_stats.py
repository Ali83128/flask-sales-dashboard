from datetime import datetime

import pytest

from app.models import Order


def _expected(start, end):
    rows = Order.query.filter(Order.created_at >= start, Order.created_at < end).all()
    paid = [o for o in rows if o.status == "paid"]
    refunded = [o for o in rows if o.status == "refunded"]
    revenue = round(sum(float(o.total) for o in paid), 2)
    return {
        "revenue": revenue,
        "orders": len(rows),
        "aov": round(revenue / len(paid), 2) if paid else 0.0,
        "refund_rate": round(100 * len(refunded) / (len(paid) + len(refunded)), 2),
    }


@pytest.mark.parametrize("range_key", ["30d", "90d", "12m"])
def test_stats_api_matches_raw_orders(auth_client, range_key):
    payload = auth_client.get(f"/api/stats?range={range_key}").get_json()
    start = datetime.fromisoformat(payload["start"])
    end = datetime.fromisoformat(payload["end"])
    assert payload["range"] == range_key
    assert payload["kpis"] == pytest.approx(_expected(start, end))


def test_revenue_series_adds_up_to_revenue(auth_client):
    payload = auth_client.get("/api/stats?range=90d").get_json()
    assert sum(payload["revenue_series"]["values"]) == pytest.approx(payload["kpis"]["revenue"], abs=0.05)
    assert len(payload["revenue_series"]["labels"]) == len(payload["revenue_series"]["values"])


def test_breakdowns_are_sorted_and_consistent(auth_client):
    payload = auth_client.get("/api/stats?range=12m").get_json()
    top = [p["revenue"] for p in payload["top_products"]]
    assert top == sorted(top, reverse=True) and len(top) == 5
    regions = payload["by_region"]
    assert sum(r["revenue"] for r in regions) == pytest.approx(payload["kpis"]["revenue"], abs=0.05)


def test_twelve_months_has_no_fake_comparison(auth_client):
    payload = auth_client.get("/api/stats?range=12m").get_json()
    assert payload["previous"] is None
    assert set(payload["change_pct"].values()) == {None}


def test_short_ranges_compare_with_previous_period(auth_client):
    payload = auth_client.get("/api/stats?range=30d").get_json()
    assert payload["previous"] is not None
    prev, cur = payload["previous"]["orders"], payload["kpis"]["orders"]
    assert payload["change_pct"]["orders"] == round(100 * (cur - prev) / prev, 1)


def test_unknown_range_falls_back_to_default(auth_client):
    assert auth_client.get("/api/stats?range=forever").get_json()["range"] == "90d"
