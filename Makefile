.PHONY: install test lint run db schema

install:
	python -m pip install -r requirements-dev.txt

test:
	python -m pytest -q

lint:
	python -m ruff check .

run:
	PYTHONPATH=src python -m uvicorn app.main:app --reload --port 8000

db:
	PYTHONPATH=src python scripts/create_database.py

schema:
	PYTHONPATH=src python scripts/print_schema.py
