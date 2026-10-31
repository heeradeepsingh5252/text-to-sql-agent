"""Parser-based validation for read-only SQLite SELECT statements."""
from __future__ import annotations

from dataclasses import dataclass

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    sql: str | None = None
    error: str | None = None


def _contains_sql_comment(sql: str) -> bool:
    """Detect SQL comment openers outside quoted strings and identifiers.

    We reject comments instead of attempting to interpret them. This avoids
    comment-based keyword hiding and makes generated SQL easier to audit.
    """
    index = 0
    length = len(sql)
    quote_end = None
    while index < length:
        char = sql[index]
        if quote_end is not None:
            if char == quote_end:
                # SQL escapes a quote by doubling it: 'it''s', "a""b", `a``b`.
                if index + 1 < length and sql[index + 1] == quote_end:
                    index += 2
                    continue
                quote_end = None
            elif quote_end == "]" and char == "]":
                quote_end = None
            index += 1
            continue

        if char in ("'", '"', "`", "["):
            quote_end = "]" if char == "[" else char
            index += 1
            continue
        if sql.startswith("--", index) or sql.startswith("/*", index) or char == "#":
            return True
        index += 1
    return False


def _write_expression_types() -> tuple[type[exp.Expression], ...]:
    names = (
        "Insert", "Update", "Delete", "Create", "Drop", "Alter", "Merge",
        "TruncateTable", "Command", "Transaction", "Commit", "Rollback",
        "Pragma", "Attach", "Detach", "Into", "Lock",
    )
    return tuple(
        expression_type
        for name in names
        if (expression_type := getattr(exp, name, None)) is not None
    )


def _is_query_expression(expression: exp.Expression) -> bool:
    query_types = tuple(
        expression_type
        for name in ("Select", "Union", "Intersect", "Except")
        if (expression_type := getattr(exp, name, None)) is not None
    )
    return isinstance(expression, query_types)


def _limit_query(query: exp.Expression, max_rows: int) -> None:
    """Add a safe LIMIT or lower a larger numeric LIMIT in-place."""
    limit = query.args.get("limit")
    if limit is not None:
        value = limit.args.get("expression")
        if isinstance(value, exp.Literal) and not value.is_string:
            try:
                requested = int(value.this)
            except (TypeError, ValueError):
                requested = max_rows + 1
            if 0 <= requested <= max_rows:
                return
        # Dynamic and negative limits are replaced with the configured cap.
    query.limit(max_rows, copy=False)


def validate_select_only(sql: str, max_rows: int = 200) -> ValidationResult:
    """Accept one read-only SELECT/CTE query and enforce a maximum row count.

    SQLGlot parses SQL into an AST. The validator checks the root query type
    and every AST node, then renders normalized SQLite SQL with a capped LIMIT.
    Any uncertainty or parsing error fails closed.
    """
    if not isinstance(sql, str) or not sql.strip():
        return ValidationResult(False, error="SQL is empty")
    if max_rows < 1:
        return ValidationResult(False, error="max_rows must be at least 1")
    if _contains_sql_comment(sql):
        return ValidationResult(False, error="SQL comments are not permitted")

    try:
        statements = [statement for statement in sqlglot.parse(sql, read="sqlite") if statement]
    except ParseError as error:
        details = getattr(error, "errors", None) or []
        description = details[0].get("description", str(error)) if details else str(error)
        return ValidationResult(False, error=f"SQL parse error: {description}")
    except Exception as error:  # Unknown parser failures must also fail closed.
        return ValidationResult(False, error=f"SQL parse error: {error}")

    if len(statements) != 1:
        return ValidationResult(False, error="Exactly one SQL statement is allowed")

    query = statements[0]
    if not _is_query_expression(query):
        return ValidationResult(False, error="Only SELECT queries are allowed")

    write_types = _write_expression_types()
    for node in query.walk():
        if write_types and isinstance(node, write_types):
            return ValidationResult(False, error=f"Write or administrative SQL is not allowed: {node.key}")
        # CTE bodies and nested query expressions must themselves be SELECTs.
        if isinstance(node, exp.Query) and not _is_query_expression(node):
            return ValidationResult(False, error="Only SELECT queries are allowed inside subqueries and CTEs")

    try:
        _limit_query(query, max_rows)
        normalized = query.sql(dialect="sqlite", pretty=False).strip().rstrip(";")
    except Exception as error:
        return ValidationResult(False, error=f"Could not safely normalize SQL: {error}")

    if not normalized:
        return ValidationResult(False, error="SQL produced an empty query")
    return ValidationResult(True, sql=normalized)
