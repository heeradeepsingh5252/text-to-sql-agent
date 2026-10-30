"""Tests for synthetic database creation and SQLite schema introspection."""

from pathlib import Path

import pytest

from app.database import create_database
from app.schema import get_schema_description

EXPECTED_TABLES = ("products", "sales_transactions", "inventory_snapshot")


@pytest.fixture()
def pharma_db(tmp_path: Path) -> Path:
    return create_database(tmp_path / "pharma.db", seed=42)


def test_database_contains_expected_tables(pharma_db: Path) -> None:
    description = get_schema_description(pharma_db)
    for table in EXPECTED_TABLES:
        assert f"TABLE {table}" in description


def test_schema_contains_expected_columns(pharma_db: Path) -> None:
    description = get_schema_description(pharma_db)
    expected_columns = (
        "product_id",
        "product_name",
        "category",
        "unit_cost",
        "list_price",
        "transaction_id",
        "transaction_date",
        "region",
        "units_sold",
        "revenue",
        "estimated_gross_profit",
        "margin_pct",
        "snapshot_date",
        "stock_on_hand",
        "reorder_flag",
    )
    for column in expected_columns:
        assert column in description


def test_schema_contains_sample_rows_and_relationships(pharma_db: Path) -> None:
    description = get_schema_description(pharma_db, sample_rows=2)
    assert "Sample rows (up to 2):" in description
    assert "sales_transactions.product_id -> products.product_id" in description
    assert "inventory_snapshot.product_id -> products.product_id" in description


def test_database_has_deterministic_row_counts(pharma_db: Path) -> None:
    import sqlite3

    with sqlite3.connect(pharma_db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 8
        assert connection.execute("SELECT COUNT(*) FROM sales_transactions").fetchone()[0] == 600
        assert connection.execute("SELECT COUNT(*) FROM inventory_snapshot").fetchone()[0] == 768


def test_missing_database_raises_clear_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="SQLite database not found"):
        get_schema_description(tmp_path / "missing.db")


def test_negative_sample_rows_are_rejected(tmp_path: Path) -> None:
    db_path = create_database(tmp_path / "pharma.db")
    with pytest.raises(ValueError, match="sample_rows cannot be negative"):
        get_schema_description(db_path, sample_rows=-1)
