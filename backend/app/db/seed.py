"""Deterministic seed data for the sample ecommerce database."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.db.engine import create_db_engine, create_session_factory
from app.db.models import Base, Category, Customer, Order, OrderItem, Product

CATEGORIES: list[dict[str, str]] = [
    {"name": "Electronics", "description": "Phones, laptops, and accessories"},
    {"name": "Home", "description": "Kitchen and living essentials"},
    {"name": "Sports", "description": "Fitness and outdoor gear"},
    {"name": "Books", "description": "Fiction and reference titles"},
]

PRODUCTS: list[dict[str, object]] = [
    {"name": "Wireless Headphones", "category": "Electronics", "unit_price": "89.99", "stock_quantity": 120},
    {"name": "USB-C Hub", "category": "Electronics", "unit_price": "39.50", "stock_quantity": 200},
    {"name": "4K Monitor", "category": "Electronics", "unit_price": "329.00", "stock_quantity": 45},
    {"name": "Ceramic Mug Set", "category": "Home", "unit_price": "24.00", "stock_quantity": 300},
    {"name": "Desk Lamp", "category": "Home", "unit_price": "45.75", "stock_quantity": 150},
    {"name": "Yoga Mat", "category": "Sports", "unit_price": "32.00", "stock_quantity": 180},
    {"name": "Running Shoes", "category": "Sports", "unit_price": "110.00", "stock_quantity": 90},
    {"name": "Resistance Bands", "category": "Sports", "unit_price": "18.50", "stock_quantity": 220},
    {"name": "SQL in Practice", "category": "Books", "unit_price": "42.00", "stock_quantity": 75},
    {"name": "Data Modeling Guide", "category": "Books", "unit_price": "38.00", "stock_quantity": 60},
]

CUSTOMERS: list[dict[str, str]] = [
    {"full_name": "Ava Nguyen", "email": "ava.nguyen@example.com", "city": "Austin", "country": "USA"},
    {"full_name": "Ben Carter", "email": "ben.carter@example.com", "city": "Seattle", "country": "USA"},
    {"full_name": "Clara Schmidt", "email": "clara.schmidt@example.com", "city": "Berlin", "country": "Germany"},
    {"full_name": "Diego Alvarez", "email": "diego.alvarez@example.com", "city": "Madrid", "country": "Spain"},
    {"full_name": "Elena Rossi", "email": "elena.rossi@example.com", "city": "Milan", "country": "Italy"},
    {"full_name": "Farid Hassan", "email": "farid.hassan@example.com", "city": "Toronto", "country": "Canada"},
]

# (customer_email, order_date, status, [(product_name, qty), ...])
ORDERS: list[tuple[str, date, str, list[tuple[str, int]]]] = [
    (
        "ava.nguyen@example.com",
        date(2025, 1, 12),
        "completed",
        [("Wireless Headphones", 1), ("USB-C Hub", 2)],
    ),
    (
        "ben.carter@example.com",
        date(2025, 1, 18),
        "completed",
        [("4K Monitor", 1), ("Desk Lamp", 1)],
    ),
    (
        "clara.schmidt@example.com",
        date(2025, 2, 3),
        "completed",
        [("Yoga Mat", 1), ("Resistance Bands", 2)],
    ),
    (
        "diego.alvarez@example.com",
        date(2025, 2, 14),
        "shipped",
        [("Running Shoes", 1), ("SQL in Practice", 1)],
    ),
    (
        "elena.rossi@example.com",
        date(2025, 3, 1),
        "completed",
        [("Ceramic Mug Set", 3), ("Data Modeling Guide", 1)],
    ),
    (
        "farid.hassan@example.com",
        date(2025, 3, 9),
        "completed",
        [("Wireless Headphones", 1), ("Yoga Mat", 1), ("USB-C Hub", 1)],
    ),
    (
        "ava.nguyen@example.com",
        date(2025, 3, 22),
        "completed",
        [("4K Monitor", 1)],
    ),
    (
        "ben.carter@example.com",
        date(2025, 4, 5),
        "cancelled",
        [("Desk Lamp", 2)],
    ),
    (
        "clara.schmidt@example.com",
        date(2025, 4, 16),
        "completed",
        [("SQL in Practice", 2), ("Data Modeling Guide", 1)],
    ),
    (
        "diego.alvarez@example.com",
        date(2025, 5, 2),
        "completed",
        [("Running Shoes", 1), ("Resistance Bands", 3)],
    ),
]


def _product_price_map(session: Session) -> dict[str, Decimal]:
    rows = session.scalars(select(Product)).all()
    return {row.name: Decimal(row.unit_price) for row in rows}


def seed_session(session: Session) -> dict[str, int]:
    """Insert seed rows into an empty (or cleared) session and return counts."""
    categories = [
        Category(name=item["name"], description=item["description"]) for item in CATEGORIES
    ]
    session.add_all(categories)
    session.flush()
    category_ids = {category.name: category.id for category in categories}

    products = [
        Product(
            name=str(item["name"]),
            category_id=category_ids[str(item["category"])],
            unit_price=Decimal(str(item["unit_price"])),
            stock_quantity=int(item["stock_quantity"]),
        )
        for item in PRODUCTS
    ]
    session.add_all(products)
    session.flush()

    customers = [Customer(**item) for item in CUSTOMERS]
    session.add_all(customers)
    session.flush()
    customer_ids = {customer.email: customer.id for customer in customers}
    prices = _product_price_map(session)
    product_ids = {product.name: product.id for product in products}

    order_count = 0
    item_count = 0
    for email, order_date, status, lines in ORDERS:
        order = Order(
            customer_id=customer_ids[email],
            order_date=order_date,
            status=status,
        )
        session.add(order)
        session.flush()
        order_count += 1
        for product_name, quantity in lines:
            session.add(
                OrderItem(
                    order_id=order.id,
                    product_id=product_ids[product_name],
                    quantity=quantity,
                    unit_price=prices[product_name],
                )
            )
            item_count += 1

    session.commit()
    return {
        "categories": len(categories),
        "products": len(products),
        "customers": len(customers),
        "orders": order_count,
        "order_items": item_count,
    }


def clear_all_tables(engine: Engine) -> None:
    """Drop and recreate all ORM tables."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def database_is_empty(session: Session) -> bool:
    total = session.scalar(select(func.count()).select_from(Category))
    return int(total or 0) == 0


def init_database(engine: Engine, *, reset: bool = False) -> dict[str, int]:
    """Create schema if needed, optionally wipe, then seed when empty."""
    if reset:
        clear_all_tables(engine)
    else:
        Base.metadata.create_all(bind=engine)

    SessionLocal = create_session_factory(engine)
    with SessionLocal() as session:
        if reset or database_is_empty(session):
            return seed_session(session)
        return {
            "categories": int(session.scalar(select(func.count()).select_from(Category)) or 0),
            "products": int(session.scalar(select(func.count()).select_from(Product)) or 0),
            "customers": int(session.scalar(select(func.count()).select_from(Customer)) or 0),
            "orders": int(session.scalar(select(func.count()).select_from(Order)) or 0),
            "order_items": int(session.scalar(select(func.count()).select_from(OrderItem)) or 0),
        }


def ensure_database(path: Path | None = None, *, reset: bool = False) -> dict[str, int]:
    """Ensure the configured (or given) SQLite file exists and is seeded."""
    if path is not None:
        from app.db.engine import sqlite_url_for_path
        from sqlalchemy import create_engine, event

        path.parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(
            sqlite_url_for_path(path),
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    else:
        engine = create_db_engine()

    return init_database(engine, reset=reset)


def table_row_counts(engine: Engine) -> dict[str, int]:
    """Return row counts for all ecommerce tables."""
    SessionLocal = create_session_factory(engine)
    with SessionLocal() as session:
        return {
            "categories": int(session.scalar(select(func.count()).select_from(Category)) or 0),
            "products": int(session.scalar(select(func.count()).select_from(Product)) or 0),
            "customers": int(session.scalar(select(func.count()).select_from(Customer)) or 0),
            "orders": int(session.scalar(select(func.count()).select_from(Order)) or 0),
            "order_items": int(session.scalar(select(func.count()).select_from(OrderItem)) or 0),
        }


def smoke_top_products_by_sales(engine: Engine, limit: int = 5) -> list[tuple[str, float]]:
    """Example analytics query used to verify the seed supports NL→SQL demos."""
    sql = text(
        """
        SELECT p.name AS product,
               ROUND(SUM(oi.quantity * oi.unit_price), 2) AS sales
        FROM order_items oi
        JOIN products p ON p.id = oi.product_id
        JOIN orders o ON o.id = oi.order_id
        WHERE o.status != 'cancelled'
        GROUP BY p.id, p.name
        ORDER BY sales DESC
        LIMIT :limit
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"limit": limit}).all()
    return [(str(name), float(sales)) for name, sales in rows]
