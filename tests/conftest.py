import re

import pytest

from app import create_app
from app.extensions import db
from app.seed import DEMO_EMAIL, DEMO_PASSWORD, seed_database


@pytest.fixture()
def app():
    app = create_app("testing")
    with app.app_context():
        seed_database(order_count=400, seed=7)
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def csrf_from(response):
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True))
    assert match, "page should render a CSRF token"
    return match.group(1)


@pytest.fixture()
def auth_client(client):
    token = csrf_from(client.get("/login"))
    response = client.post(
        "/login", data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD, "csrf_token": token}
    )
    assert response.status_code == 302
    client.csrf = token
    return client
