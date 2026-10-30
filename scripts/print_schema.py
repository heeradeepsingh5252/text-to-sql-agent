"""Print a human-readable description of the pharma database schema."""

from pathlib import Path

from app.config import DATABASE_PATH
from app.schema import get_schema_description

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    database_path = DATABASE_PATH if DATABASE_PATH.is_absolute() else ROOT / DATABASE_PATH
    print(get_schema_description(database_path, sample_rows=2))


if __name__ == "__main__":
    main()
