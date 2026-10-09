import re
from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from sqlalchemy import func

from .extensions import db
from .models import CATEGORIES, Order, Product
from .security import login_required

bp = Blueprint("products", __name__, url_prefix="/products")

SKU_PATTERN = re.compile(r"^[A-Z0-9-]{3,20}$")


def validate_product(form, product=None):
    errors = {}
    data = {
        "name": (form.get("name") or "").strip(),
        "sku": (form.get("sku") or "").strip().upper(),
        "category": form.get("category") or "",
        "price": (form.get("price") or "").strip(),
        "stock": (form.get("stock") or "").strip(),
        "active": form.get("active") == "on",
    }
    if not data["name"]:
        errors["name"] = "Name is required."
    elif len(data["name"]) > 80:
        errors["name"] = "Name must be 80 characters or fewer."

    if not SKU_PATTERN.match(data["sku"]):
        errors["sku"] = "SKU must be 3-20 characters: letters, digits or dashes."
    else:
        clash = Product.query.filter(Product.sku == data["sku"])
        if product is not None:
            clash = clash.filter(Product.id != product.id)
        if clash.first():
            errors["sku"] = "That SKU is already in use."

    if data["category"] not in CATEGORIES:
        errors["category"] = "Choose a category."

    try:
        price = Decimal(data["price"])
        if not price.is_finite() or price <= 0 or price > 100000:
            raise InvalidOperation
        data["price"] = price.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        errors["price"] = "Price must be a number between 0.01 and 100,000."

    try:
        stock = int(data["stock"])
        if stock < 0 or stock > 1_000_000:
            raise ValueError
        data["stock"] = stock
    except ValueError:
        errors["stock"] = "Stock must be a whole number, 0 or more."

    return data, errors


@bp.route("/")
@login_required
def index():
    category = request.args.get("category", "")
    query = (
        db.session.query(Product, func.count(Order.id), func.coalesce(func.sum(Order.total), 0))
        .outerjoin(Order, (Order.product_id == Product.id) & (Order.status == "paid"))
        .group_by(Product.id)
        .order_by(Product.category, Product.name)
    )
    if category in CATEGORIES:
        query = query.filter(Product.category == category)
    return render_template(
        "products/index.html", rows=query.all(), categories=CATEGORIES, active_category=category
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    form, errors = {}, {}
    if request.method == "POST":
        form, errors = validate_product(request.form)
        if not errors:
            product = Product(**form)
            db.session.add(product)
            db.session.commit()
            flash(f"Product {product.sku} created.", "success")
            return redirect(url_for("products.index"))
        flash("Please fix the highlighted fields.", "error")
    return render_template("products/form.html", form=form, errors=errors, product=None, categories=CATEGORIES)


@bp.route("/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def edit(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    form = {
        "name": product.name, "sku": product.sku, "category": product.category,
        "price": product.price, "stock": product.stock, "active": product.active,
    }
    errors = {}
    if request.method == "POST":
        form, errors = validate_product(request.form, product)
        if not errors:
            for key, value in form.items():
                setattr(product, key, value)
            db.session.commit()
            flash(f"Product {product.sku} updated.", "success")
            return redirect(url_for("products.index"))
        flash("Please fix the highlighted fields.", "error")
    return render_template("products/form.html", form=form, errors=errors, product=product, categories=CATEGORIES)


@bp.route("/<int:product_id>/delete", methods=["POST"])
@login_required
def delete(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    if Order.query.filter_by(product_id=product.id).first():
        product.active = False
        db.session.commit()
        flash(f"{product.sku} has order history, so it was archived instead of deleted.", "info")
    else:
        db.session.delete(product)
        db.session.commit()
        flash(f"Product {product.sku} deleted.", "success")
    return redirect(url_for("products.index"))
