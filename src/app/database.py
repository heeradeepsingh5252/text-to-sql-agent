"""Create a small, deterministic synthetic pharmaceutical distribution database."""
from __future__ import annotations

import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

PRODUCTS = (
    (1, "Cardiava 10 mg", "Cardiology", 42.0, 65.0, 30),
    (2, "Glucozen 500 mg", "Diabetes Care", 18.0, 29.0, 80),
    (3, "Respira 100 mcg", "Respiratory", 75.0, 110.0, 25),
    (4, "Neurocalm 25 mg", "Neurology", 31.0, 49.0, 35),
    (5, "Gastrolyn 20 mg", "Gastroenterology", 22.0, 36.0, 45),
    (6, "Dermasol Cream", "Dermatology", 55.0, 85.0, 20),
    (7, "Arthriflex 200 mg", "Pain Management", 27.0, 44.0, 50),
    (8, "Immunora 5 mg", "Immunology", 96.0, 145.0, 15),
)
REGIONS = ("Hyderabad", "Mumbai", "Delhi", "Bengaluru")


def create_database(db_path: str | Path, seed: int = 42) -> Path:
    destination = Path(db_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    rng = random.Random(seed)
    connection = sqlite3.connect(destination)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript("""
            CREATE TABLE products (
                product_id INTEGER PRIMARY KEY, product_name TEXT NOT NULL,
                category TEXT NOT NULL, unit_cost REAL NOT NULL CHECK (unit_cost >= 0),
                list_price REAL NOT NULL CHECK (list_price >= unit_cost),
                reorder_level INTEGER NOT NULL CHECK (reorder_level >= 0)
            );
            CREATE TABLE sales_transactions (
                transaction_id INTEGER PRIMARY KEY, transaction_date TEXT NOT NULL,
                product_id INTEGER NOT NULL, region TEXT NOT NULL,
                units_sold INTEGER NOT NULL CHECK (units_sold > 0),
                revenue REAL NOT NULL CHECK (revenue >= 0),
                estimated_gross_profit REAL NOT NULL, margin_pct REAL NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products(product_id)
            );
            CREATE TABLE inventory_snapshot (
                snapshot_id INTEGER PRIMARY KEY, snapshot_date TEXT NOT NULL,
                product_id INTEGER NOT NULL, region TEXT NOT NULL,
                stock_on_hand INTEGER NOT NULL CHECK (stock_on_hand >= 0),
                reorder_flag INTEGER NOT NULL CHECK (reorder_flag IN (0, 1)),
                FOREIGN KEY (product_id) REFERENCES products(product_id),
                UNIQUE (snapshot_date, product_id, region)
            );
        """)
        connection.executemany(
            "INSERT INTO products VALUES (?, ?, ?, ?, ?, ?)", PRODUCTS
        )
        start_date = date(2024, 1, 1)
        date_span = (date(2025, 12, 31) - start_date).days
        sales_rows = []
        for transaction_id in range(1, 601):
            product = rng.choice(PRODUCTS)
            product_id, _, _, unit_cost, list_price, _ = product
            units = rng.randint(2, 45)
            region = rng.choice(REGIONS)
            transaction_date = start_date + timedelta(days=rng.randint(0, date_span))
            revenue = round(units * list_price * rng.uniform(0.94, 1.0), 2)
            gross_profit = round(revenue - units * unit_cost, 2)
            margin = round(gross_profit / revenue * 100, 2) if revenue else 0.0
            sales_rows.append((transaction_id, transaction_date.isoformat(), product_id,
                               region, units, revenue, gross_profit, margin))
        connection.executemany("INSERT INTO sales_transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?)", sales_rows)
        inventory_rows = []
        snapshot_id = 1
        for year in (2024, 2025):
            for month in range(1, 13):
                snapshot_date = date(year, month, 1).isoformat()
                for product in PRODUCTS:
                    product_id, _, _, _, _, reorder_level = product
                    for region in REGIONS:
                        stock = rng.randint(5, 180)
                        inventory_rows.append((snapshot_id, snapshot_date, product_id, region,
                                               stock, int(stock <= reorder_level)))
                        snapshot_id += 1
        connection.executemany("INSERT INTO inventory_snapshot VALUES (?, ?, ?, ?, ?, ?)", inventory_rows)
        connection.commit()
    finally:
        connection.close()
    return destination
