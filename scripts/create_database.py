"""Create the local synthetic pharma SQLite database."""

from pathlib import Path

from app.database import create_database

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    destination = create_database(ROOT / "data" / "pharma.db")
    print(f"Created synthetic database: {destination.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
