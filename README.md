# Pharma Text-to-SQL Agent

A schema-aware text-to-SQL assistant for a synthetic pharmaceutical distribution database. It is being built in phases, with read-only SQL validation as the central safety requirement.

## Phase 1: database and schema introspection

The current database contains synthetic sales transactions, product information, and inventory snapshots. The data is generated locally with a fixed seed and is not real Sanofi or customer data.

Run the schema inspection from the repository root:

```bash
PYTHONPATH=src python scripts/print_schema.py
```

Create or regenerate the database:

```bash
PYTHONPATH=src python scripts/create_database.py
```

Run tests:

```bash
PYTHONPATH=src python -m pytest -q
```

Later phases will add SQL validation, LLM-based query generation, safe execution, answer generation, API endpoints, evaluation, and fuller documentation.
