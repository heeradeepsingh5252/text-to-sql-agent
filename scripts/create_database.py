"""Create the local synthetic pharma SQLite database."""
from app.config import Settings
from app.database import create_database


def main() -> None:
    settings = Settings.from_env()
    destination = create_database(settings.database_path)
    print(f"Created synthetic database: {destination}")


if __name__ == "__main__":
    main()
