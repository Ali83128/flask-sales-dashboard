from app.seed import DEMO_EMAIL, DEMO_PASSWORD

from .conftest import csrf_from


def test_login_page_renders(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Sign in" in response.data


def test_wrong_password_is_rejected(client):
    token = csrf_from(client.get("/login"))
    response = client.post("/login", data={"email": DEMO_EMAIL, "password": "nope", "csrf_token": token})
    assert response.status_code == 200
    assert b"Incorrect email or password" in response.data
    assert client.get("/").status_code == 302


def test_login_then_logout(client):
    token = csrf_from(client.get("/login"))
    response = client.post("/login", data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD, "csrf_token": token})
    assert response.headers["Location"] == "/"
    assert client.get("/").status_code == 200

    response = client.post("/logout", data={"csrf_token": token})
    assert response.status_code == 302
    assert client.get("/").status_code == 302


def test_post_without_csrf_token_is_rejected(client):
    response = client.post("/login", data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    assert response.status_code == 400
    assert client.get("/").status_code == 302


def test_next_parameter_cannot_redirect_offsite(client):
    token = csrf_from(client.get("/login"))
    response = client.post(
        "/login?next=https://evil.example/steal",
        data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD, "csrf_token": token},
    )
    assert response.headers["Location"] == "/"


def test_next_parameter_keeps_local_path(client):
    token = csrf_from(client.get("/login"))
    response = client.post(
        "/login?next=/orders/?status=paid",
        data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD, "csrf_token": token},
    )
    assert response.headers["Location"] == "/orders/?status=paid"
