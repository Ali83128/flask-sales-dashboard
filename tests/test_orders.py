import csv
import io

from app.models import Order


def test_status_and_region_filters(auth_client):
    payload = auth_client.get("/api/orders?status=refunded&region=West&per_page=200").get_json()
    expected = Order.query.filter_by(status="refunded", region="West").count()
    assert payload["total"] == expected
    assert all(o["status"] == "refunded" and o["region"] == "West" for o in payload["items"])


def test_invalid_filter_values_are_ignored(auth_client):
    payload = auth_client.get("/api/orders?status=hacked&region=Mars").get_json()
    assert payload["filters"] == {"q": "", "status": "", "region": ""}
    assert payload["total"] == Order.query.count()


def test_search_by_order_number(auth_client):
    number = Order.query.first().number
    payload = auth_client.get(f"/api/orders?q={number}").get_json()
    assert [o["number"] for o in payload["items"]] == [number]


def test_csv_export_respects_filters(auth_client):
    response = auth_client.get("/orders/export.csv?status=pending")
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "attachment; filename=orders-" in response.headers["Content-Disposition"]
    rows = list(csv.DictReader(io.StringIO(response.get_data(as_text=True))))
    assert len(rows) == Order.query.filter_by(status="pending").count()
    assert {r["status"] for r in rows} == {"pending"}
    assert list(rows[0].keys())[:3] == ["number", "created_at", "customer"]


def test_orders_page_paginates(auth_client):
    page_two = auth_client.get("/orders/?page=2")
    assert page_two.status_code == 200
    assert b"Page 2 of" in page_two.data
