# Phase 1 files: database setup and schema introspection

- `src/app/database.py` creates a deterministic synthetic SQLite database with products, sales transactions, and inventory snapshots.
- `src/app/schema.py` opens the database in read-only mode and describes tables, columns, sample rows, and declared or inferred relationships.
- `scripts/create_database.py` regenerates `data/pharma.db`.
- `scripts/print_schema.py` prints the schema description for inspection.
- `tests/test_schema.py` checks the three tables, important columns, sample rows, relationships, row counts, and input errors.
- `data/pharma.db` is the generated synthetic database used in later phases.

The data is synthetic and is not copied from Sanofi or any real customer system.
