# Text-to-SQL Evaluation Results

**Status: Not run yet.** No LLM evaluation metrics are claimed in this repository until `scripts/run_evaluation.py` has been run with a valid provider API key.

Run from the repository root:

```bash
PYTHONPATH=src python scripts/run_evaluation.py
```

The script executes the 20-question benchmark against the configured provider, compares returned rows with reference-query rows, and writes measured results to this file and `reports/eval_results.json`.
