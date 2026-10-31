"""Adversarial tests for parser-backed SQL validation."""
import pytest

from app.sql_guard import validate_select_only


@pytest.mark.parametrize("sql", [
    "SELECT product_name FROM products",
    "select count(*) from sales_transactions",
    "WITH totals AS (SELECT region, SUM(revenue) AS revenue FROM sales_transactions GROUP BY region) SELECT * FROM totals",
    "SELECT product_name FROM products UNION SELECT product_name FROM products",
    "SELECT 'DROP TABLE products' AS harmless_text",
])
def test_read_only_selects_are_allowed(sql: str) -> None:
    result = validate_select_only(sql, max_rows=25)
    assert result.valid
    assert result.sql
    assert "LIMIT 25" in result.sql.upper()


@pytest.mark.parametrize("sql", [
    "DROP TABLE products",
    "dRoP TABLE products",
    "SeLeCt 1; DrOp TABLE products",
    "DELETE FROM products",
    "UPDATE products SET list_price = 0",
    "INSERT INTO products VALUES (9, 'X', 'X', 1, 2, 3)",
    "CREATE TABLE bad (id INT)",
    "SELECT 1; DROP TABLE products",
    "SELECT * FROM products -- hide the rest",
    "SELECT * FROM products /* comment */",
    "SELECT * FROM products # comment",
    "WITH gone AS (DELETE FROM products RETURNING *) SELECT * FROM gone",
    "SELECT * FROM (UPDATE products SET list_price = 0)",
    "PRAGMA table_info(products)",
    "ATTACH DATABASE 'x.db' AS x",
    "not valid sql !!!",
    "",
])
def test_unsafe_or_invalid_sql_is_rejected(sql: str) -> None:
    result = validate_select_only(sql)
    assert not result.valid
    assert result.error


def test_comment_marker_inside_string_is_not_a_comment() -> None:
    result = validate_select_only("SELECT '-- not a comment' AS note")
    assert result.valid


def test_existing_small_limit_is_preserved() -> None:
    result = validate_select_only("SELECT * FROM products LIMIT 5", max_rows=20)
    assert result.valid
    assert "LIMIT 5" in result.sql.upper()


def test_existing_large_limit_is_capped() -> None:
    result = validate_select_only("SELECT * FROM products LIMIT 9999", max_rows=50)
    assert result.valid
    assert "LIMIT 50" in result.sql.upper()


def test_negative_limit_is_replaced() -> None:
    result = validate_select_only("SELECT * FROM products LIMIT -1", max_rows=30)
    assert result.valid
    assert "LIMIT 30" in result.sql.upper()


def test_multiple_statements_are_rejected_even_with_trailing_semicolon() -> None:
    result = validate_select_only("SELECT 1; SELECT 2")
    assert not result.valid


def test_max_rows_must_be_positive() -> None:
    assert not validate_select_only("SELECT 1", max_rows=0).valid
