"""Print a human-readable description of the pharma database schema."""
from app.config import Settings
from app.schema import get_schema_description


def main() -> None:
    settings = Settings.from_env()
    print(get_schema_description(settings.database_path, sample_rows=2))


if __name__ == "__main__":
    main()
