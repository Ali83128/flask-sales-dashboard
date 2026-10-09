from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db

CATEGORIES = ["Electronics", "Home & Kitchen", "Outdoors", "Office", "Health"]
REGIONS = ["North", "South", "East", "West", "Central", "Online"]
STATUSES = ["paid", "pending", "refunded"]


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    category = db.Column(db.String(40), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    active = db.Column(db.Boolean, nullable=False, default=True)
    orders = db.relationship("Order", back_populates="product")


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    region = db.Column(db.String(20), nullable=False)
    orders = db.relationship("Order", back_populates="customer")


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    total = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.String(12), nullable=False, index=True)
    region = db.Column(db.String(20), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)

    customer = db.relationship("Customer", back_populates="orders")
    product = db.relationship("Product", back_populates="orders")

    def to_dict(self):
        return {
            "number": self.number,
            "created_at": self.created_at.isoformat(timespec="seconds"),
            "customer": self.customer.name,
            "email": self.customer.email,
            "product": self.product.name,
            "sku": self.product.sku,
            "quantity": self.quantity,
            "unit_price": float(self.unit_price),
            "total": float(self.total),
            "status": self.status,
            "region": self.region,
        }
