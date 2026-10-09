import os

import click
from flask import Flask, render_template

from .config import CONFIGS
from .extensions import db
from .security import csrf_token, load_user, verify_csrf


def create_app(config_name=None, **overrides):
    config_name = config_name or os.environ.get("APP_ENV", "development")
    config_cls = CONFIGS[config_name]
    if hasattr(config_cls, "validate"):
        config_cls.validate()

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_cls)
    app.config.update(overrides)
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        os.makedirs(app.instance_path, exist_ok=True)
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(app.instance_path, "sales.db")

    db.init_app(app)

    from .api import bp as api_bp
    from .auth import bp as auth_bp
    from .dashboard import bp as dashboard_bp
    from .orders import bp as orders_bp
    from .products import bp as products_bp

    for bp in (auth_bp, dashboard_bp, orders_bp, products_bp, api_bp):
        app.register_blueprint(bp)

    app.before_request(load_user)
    app.before_request(verify_csrf)
    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.template_filter("money")
    def money(value):
        return f"${float(value or 0):,.2f}"

    @app.errorhandler(400)
    def bad_request(err):
        return render_template("error.html", code=400, message=err.description), 400

    @app.errorhandler(404)
    def not_found(err):
        return render_template("error.html", code=404, message="Page not found."), 404

    @app.cli.command("seed")
    @click.option("--orders", default=2000, show_default=True, help="Number of orders to create.")
    @click.option("--seed", "seed_value", default=42, show_default=True, help="Random seed.")
    def seed_command(orders, seed_value):
        """Reset the database and load seeded demo data."""
        from .seed import DEMO_EMAIL, DEMO_PASSWORD, seed_database

        counts = seed_database(order_count=orders, seed=seed_value)
        click.echo(
            f"Seeded {counts['products']} products, {counts['customers']} customers, "
            f"{counts['orders']} orders."
        )
        click.echo(f"Log in with {DEMO_EMAIL} / {DEMO_PASSWORD}")

    return app
