"""SQLite schema introspection for schema-aware text-to-SQL prompting."""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from urllib.parse import quote


def _read_only_connection(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"SQLite database not found: {path}")
    uri = f"file:{quote(str(path), safe='/')}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def get_schema_description(db_path: str | Path, sample_rows: int = 2) -> str:
    if sample_rows < 0:
        raise ValueError("sample_rows cannot be negative")
    sections = [f"SQLite database: {Path(db_path).name}", ""]
    relationships: set[tuple[str, str, str, str]] = set()
    with closing(_read_only_connection(db_path)) as connection:
        tables = connection.execute("""SELECT name FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name""").fetchall()
        if not tables:
            raise ValueError("The SQLite database contains no user tables")
        primary_keys: dict[str, set[str]] = {}
        table_columns: dict[str, set[str]] = {}
        for table_row in tables:
            table_name = str(table_row["name"])
            escaped_table = table_name.replace('"', '""')
            columns = connection.execute(f'PRAGMA table_info("{escaped_table}")').fetchall()
            table_columns[table_name] = {str(column["name"]) for column in columns}
            primary_keys[table_name] = {str(column["name"]) for column in columns if int(column["pk"]) > 0}
            sections.extend([f"TABLE {table_name}", "Columns:"])
            for column in columns:
                details = f"  - {column['name']} {column['type'] or 'UNDECLARED'}"
                if int(column["pk"]) > 0:
                    details += " PRIMARY KEY"
                if int(column["notnull"]):
                    details += " NOT NULL"
                sections.append(details)
            if sample_rows:
                rows = connection.execute(f'SELECT * FROM "{escaped_table}" LIMIT ?', (sample_rows,)).fetchall()
                sections.append(f"Sample rows (up to {sample_rows}):")
                sections.extend([f"  - {json.dumps(dict(row), ensure_ascii=False, default=str)}" for row in rows] or ["  - No rows available"])
            sections.append("")
            foreign_keys = connection.execute(f'PRAGMA foreign_key_list("{escaped_table}")').fetchall()
            for foreign_key in foreign_keys:
                relationships.add((table_name, str(foreign_key["from"]),
                                   str(foreign_key["table"]), str(foreign_key["to"])))
        for table_name, column_names in table_columns.items():
            for column_name in column_names:
                if column_name.endswith("_id"):
                    for target_table, target_keys in primary_keys.items():
                        if target_table != table_name and column_name in target_keys:
                            relationships.add((table_name, column_name, target_table, column_name))
    sections.append("RELATIONSHIPS")
    sections.extend([f"  - {source}.{source_col} -> {target}.{target_col}"
                     for source, source_col, target, target_col in sorted(relationships)]
                    or ["  - No foreign-key relationships detected"])
    return "\n".join(sections).strip() + "\n"
