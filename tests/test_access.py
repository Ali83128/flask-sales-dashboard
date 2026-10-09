import pytest

PAGES = ["/", "/orders/", "/orders/export.csv", "/products/", "/products/new", "/products/1/edit"]


@pytest.mark.parametrize("path", PAGES)
def test_pages_require_login(client, path):
    response = client.get(path)
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login")


@pytest.mark.parametrize("path", ["/api/stats", "/api/orders"])
def test_api_returns_401_json_when_anonymous(client, path):
    response = client.get(path)
    assert response.status_code == 401
    assert response.get_json() == {"error": "authentication required"}


@pytest.mark.parametrize("path", ["/", "/?range=30d", "/?range=12m", "/orders/", "/products/"])
def test_pages_render_when_logged_in(auth_client, path):
    assert auth_client.get(path).status_code == 200
