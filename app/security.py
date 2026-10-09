import hmac
import secrets
from functools import wraps

from flask import abort, current_app, g, jsonify, redirect, request, session, url_for

from .extensions import db
from .models import User

CSRF_SESSION_KEY = "_csrf_token"


def csrf_token():
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def verify_csrf():
    if not current_app.config.get("CSRF_ENABLED", True):
        return
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return
    expected = session.get(CSRF_SESSION_KEY)
    sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    if not expected or not sent or not hmac.compare_digest(expected, sent):
        abort(400, description="Invalid or missing CSRF token.")


def load_user():
    user_id = session.get("user_id")
    g.user = db.session.get(User, user_id) if user_id else None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.get("user") is None:
            if request.path.startswith("/api/"):
                return jsonify(error="authentication required"), 401
            return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))
        return view(*args, **kwargs)

    return wrapped
