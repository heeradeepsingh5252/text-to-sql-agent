"""Read-only SQLite execution with a VM-operation timeout and row cap."""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote


class QueryExecutionError(RuntimeError):
    """Raised when safe SQL cannot be executed."""


def execute_read_only(
    sql: str,
    database_path: str | Path,
    max_rows: int = 200,
    timeout_seconds: float = 3.0,
) -> tuple[list[dict[str, Any]], bool]:
    """Execute a validated query against an SQLite file opened in read-only mode."""
    path = Path(database_path).expanduser().resolve()
    if not path.is_file():
        raise QueryExecutionError(f"Database file does not exist: {path}")
    uri = f"file:{quote(str(path), safe='/')}?mode=ro"
    deadline = time.monotonic() + timeout_seconds
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(uri, uri=True, timeout=min(timeout_seconds, 5.0))
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
        cursor = connection.execute(sql)
        raw_rows = cursor.fetchmany(max_rows + 1)
        truncated = len(raw_rows) > max_rows
        rows = [dict(row) for row in raw_rows[:max_rows]]
        return rows, truncated
    except sqlite3.Error as error:
        raise QueryExecutionError(f"SQLite rejected the query: {error}") from error
    finally:
        if connection is not None:
            connection.close()
