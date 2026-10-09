"""Deterministic demo data: products, customers, ~2,000 orders over the last 12 months."""
import math
import random
from datetime import timedelta
from decimal import Decimal

from .extensions import db
from .models import Customer, Order, Product, User, utcnow

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demo1234"

PRODUCT_CATALOG = {
    "Electronics": [
        ("Wireless Earbuds Pro", 79.00),
        ("4K Action Camera", 189.00),
        ("Smart Watch S2", 149.00),
        ("Bluetooth Speaker Mini", 39.00),
        ("USB-C Hub 7-in-1", 45.00),
    ],
    "Home & Kitchen": [
        ("Pour-Over Coffee Set", 34.00),
        ("Cast Iron Skillet 12in", 42.00),
        ("Air Fryer XL", 119.00),
        ("Linen Throw Blanket", 58.00),
        ("Chef Knife 8in", 64.00),
    ],
    "Outdoors": [
        ("Trail Backpack 30L", 89.00),
        ("Insulated Bottle 1L", 29.00),
        ("Camping Hammock", 49.00),
        ("LED Headlamp", 24.00),
        ("Folding Camp Chair", 39.00),
    ],
    "Office": [
        ("Ergonomic Desk Chair", 249.00),
        ("Standing Desk Frame", 329.00),
        ("Mechanical Keyboard", 99.00),
        ("Monitor Arm Dual", 79.00),
        ("Desk Lamp LED", 36.00),
    ],
    "Health": [
        ("Yoga Mat Pro", 48.00),
        ("Adjustable Dumbbells", 199.00),
        ("Foam Roller", 22.00),
        ("Resistance Band Set", 27.00),
        ("Digital Scale", 31.00),
    ],
}

FIRST_NAMES = [
    "Olivia", "Liam", "Emma", "Noah", "Ava", "Mason", "Sophia", "Lucas", "Mia", "Ethan",
    "Amelia", "James", "Harper", "Aiden", "Ella", "Omar", "Layla", "Daniel", "Zara", "Leo",
    "Chloe", "Henry", "Nora", "Samuel", "Grace", "Isaac", "Hannah", "Adam", "Aria", "Ryan",
]
LAST_NAMES = [
    "Carter", "Nguyen", "Patel", "Brooks", "Khan", "Rivera", "Hughes", "Morgan", "Bennett",
    "Foster", "Reyes", "Sullivan", "Ward", "Price", "Ahmed", "Collins", "Hayes", "Murphy",
    "Ross", "Kim", "Turner", "Ellis", "Shaw", "Diaz", "Grant",
]
REGION_WEIGHTS = {"North": 16, "South": 14, "East": 18, "West": 20, "Central": 10, "Online": 22}


def _day_weight(day_index, date, days):
    trend = 1.0 + 0.45 * (day_index / days)
    season = 1.0 + 0.35 * math.exp(-((date.month - 11.5) ** 2) / 1.2)
    weekday = 1.18 if date.weekday() >= 5 else 1.0
    return trend * season * weekday


def seed_database(order_count=2000, seed=42, now=None):
    rng = random.Random(seed)
    now = (now or utcnow()).replace(microsecond=0)
    days = 365

    db.drop_all()
    db.create_all()

    user = User(email=DEMO_EMAIL, name="Demo Manager")
    user.set_password(DEMO_PASSWORD)
    db.session.add(user)

    products = []
    for c_index, (category, items) in enumerate(PRODUCT_CATALOG.items(), start=1):
        for p_index, (name, price) in enumerate(items, start=1):
            products.append(
                Product(
                    sku=f"{category[:3].upper()}-{c_index}{p_index:02d}",
                    name=name,
                    category=category,
                    price=Decimal(f"{price:.2f}"),
                    stock=rng.randint(0, 240),
                    active=True,
                )
            )
    db.session.add_all(products)

    customers = []
    used_emails = set()
    regions, region_w = zip(*REGION_WEIGHTS.items())
    while len(customers) < 150:
        first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
        email = f"{first}.{last}{rng.randint(1, 99)}@example.com".lower()
        if email in used_emails:
            continue
        used_emails.add(email)
        customers.append(
            Customer(name=f"{first} {last}", email=email, region=rng.choices(regions, region_w)[0])
        )
    db.session.add_all(customers)
    db.session.flush()

    popularity = [rng.uniform(0.4, 2.2) / (float(p.price) ** 0.35) for p in products]
    loyalty = [rng.lognormvariate(0, 0.55) for _ in customers]

    start = now - timedelta(days=days)
    day_dates = [start + timedelta(days=i) for i in range(days)]
    day_weights = [_day_weight(i, d, days) for i, d in enumerate(day_dates)]
    chosen_days = rng.choices(day_dates, day_weights, k=order_count)

    timestamps = []
    for day in chosen_days:
        ts = day.replace(hour=0, minute=0, second=0) + timedelta(
            hours=rng.choices(range(24), [1, 1, 1, 1, 1, 2, 3, 5, 7, 8, 8, 9, 9, 8, 8, 8, 8, 9, 10, 10, 9, 7, 4, 2])[0],
            minutes=rng.randint(0, 59),
            seconds=rng.randint(0, 59),
        )
        timestamps.append(min(ts, now - timedelta(minutes=1)))
    timestamps.sort()

    orders = []
    for n, created_at in enumerate(timestamps, start=1):
        product = rng.choices(products, popularity)[0]
        customer = rng.choices(customers, loyalty)[0]
        quantity = rng.choices([1, 2, 3, 4], [70, 20, 7, 3])[0]
        discount = rng.choices([1.0, 0.9, 0.85], [82, 13, 5])[0]
        unit_price = (product.price * Decimal(str(discount))).quantize(Decimal("0.01"))
        age_days = (now - created_at).days
        if age_days < 7:
            status = rng.choices(["paid", "pending"], [65, 35])[0]
        else:
            status = rng.choices(["paid", "refunded", "pending"], [925, 60, 15])[0]
        orders.append(
            Order(
                number=f"SO-{10000 + n}",
                customer_id=customer.id,
                product_id=product.id,
                quantity=quantity,
                unit_price=unit_price,
                total=unit_price * quantity,
                status=status,
                region=customer.region,
                created_at=created_at,
            )
        )
    db.session.add_all(orders)
    db.session.commit()
    return {"products": len(products), "customers": len(customers), "orders": len(orders)}
