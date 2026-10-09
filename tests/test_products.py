from app.extensions import db
from app.models import Product

VALID = {"name": "Travel Mug", "sku": "HOM-900", "category": "Home & Kitchen",
         "price": "19.50", "stock": "40", "active": "on"}


def post(client, url, **overrides):
    data = {**VALID, **overrides, "csrf_token": client.csrf}
    return client.post(url, data=data, follow_redirects=True)


def test_create_product(auth_client):
    response = post(auth_client, "/products/new")
    assert b"Product HOM-900 created." in response.data
    product = Product.query.filter_by(sku="HOM-900").one()
    assert str(product.price) == "19.50" and product.stock == 40 and product.active


def test_validation_errors_block_save(auth_client):
    before = Product.query.count()
    response = post(auth_client, "/products/new", name="", sku="x", price="-3", stock="1.5", category="Toys")
    body = response.get_data(as_text=True)
    assert "Name is required." in body
    assert "SKU must be 3-20 characters" in body
    assert "Price must be a number" in body
    assert "Stock must be a whole number" in body
    assert "Choose a category." in body
    assert Product.query.count() == before


def test_duplicate_sku_rejected(auth_client):
    existing = Product.query.first()
    response = post(auth_client, "/products/new", sku=existing.sku)
    assert b"That SKU is already in use." in response.data


def test_price_rejects_nan_and_infinity(auth_client):
    for bad in ("nan", "inf", "1e9"):
        response = post(auth_client, "/products/new", price=bad, sku=f"HOM-{len(bad)}99")
        assert b"Price must be a number" in response.data


def test_edit_product_keeps_own_sku(auth_client):
    product = Product.query.first()
    response = post(auth_client, f"/products/{product.id}/edit", sku=product.sku, name="Renamed Item")
    assert b"updated." in response.data
    assert db.session.get(Product, product.id).name == "Renamed Item"


def test_delete_archives_product_with_orders(auth_client):
    product = Product.query.filter(Product.orders.any()).first()
    auth_client.post(f"/products/{product.id}/delete", data={"csrf_token": auth_client.csrf})
    refreshed = db.session.get(Product, product.id)
    assert refreshed is not None and refreshed.active is False


def test_delete_removes_unused_product(auth_client):
    post(auth_client, "/products/new")
    product = Product.query.filter_by(sku="HOM-900").one()
    auth_client.post(f"/products/{product.id}/delete", data={"csrf_token": auth_client.csrf})
    assert Product.query.filter_by(sku="HOM-900").first() is None


def test_edit_missing_product_is_404(auth_client):
    assert auth_client.get("/products/9999/edit").status_code == 404
