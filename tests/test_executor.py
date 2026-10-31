"""Tests for query-only SQLite execution."""
import sqlite3
from pathlib import Path

import pytest

from app.executor import QueryExecutionError, execute_read_only
from app.sql_guard import validate_select_only


@pytest.fixture()
def sample_db(tmp_path: Path) -> Path:
    path = tmp_path / "sample.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE products (product_id INTEGER PRIMARY KEY, product_name TEXT)")
        connection.executemany("INSERT INTO products VALUES (?, ?)", [(1, "A"), (2, "B"), (3, "C")])
    return path


def test_read_only_query_returns_dict_rows(sample_db: Path) -> None:
    safe = validate_select_only("SELECT product_name FROM products ORDER BY product_id")
    rows, truncated = execute_read_only(safe.sql, sample_db)
    assert rows == [{"product_name": "A"}, {"product_name": "B"}, {"product_name": "C"}]
    assert not truncated


def test_executor_enforces_row_limit(sample_db: Path) -> None:
    rows, truncated = execute_read_only("SELECT * FROM products", sample_db, max_rows=2)
    assert len(rows) == 2
    assert truncated


def test_query_only_blocks_writes_even_without_validator(sample_db: Path) -> None:
    with pytest.raises(QueryExecutionError, match="readonly"):
        execute_read_only("DELETE FROM products", sample_db)


def test_missing_database_fails_clearly(tmp_path: Path) -> None:
    with pytest.raises(QueryExecutionError, match="does not exist"):
        execute_read_only("SELECT 1", tmp_path / "absent.db")
