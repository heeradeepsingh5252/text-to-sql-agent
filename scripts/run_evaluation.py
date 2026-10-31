"""Run the 20-question evaluation against a configured live LLM provider.

This script makes real provider requests. It writes results only after execution;
never replace a not-run report with invented or hand-estimated metrics.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.agent import TextToSQLAgent
from app.config import Settings
from app.executor import execute_read_only

ROOT = Path(__file__).resolve().parents[1]


def canonical(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: json.dumps(row, sort_keys=True, default=str))


def main() -> None:
    settings = Settings.from_env()
    dataset = json.loads((ROOT / "evaluation" / "questions.json").read_text(encoding="utf-8"))
    agent = TextToSQLAgent(settings)
    results = []
    for item in dataset:
        record: dict[str, Any] = {"id": item["id"], "question": item["question"]}
        try:
            actual = agent.ask(item["question"])
            expected_rows, _ = execute_read_only(
                item["expected_sql"], settings.database_path,
                max_rows=settings.max_query_rows, timeout_seconds=settings.query_timeout_seconds,
            )
            matched = canonical(actual.rows) == canonical(expected_rows)
            record.update({
                "success": True,
                "result_match": matched,
                "retries": actual.retries,
                "row_count": actual.row_count,
                "sql": actual.sql,
                "error": None,
            })
        except Exception as error:  # Record failures and continue through the evaluation set.
            record.update({"success": False, "result_match": False, "retries": int(getattr(error, "retries", 0)), "row_count": 0,
                           "sql": None, "error": str(error)})
        results.append(record)
        print(f"{item['id']}: success={record['success']} result_match={record['result_match']} retries={record['retries']}")

    total = len(results)
    successful = sum(bool(item["success"]) for item in results)
    matched = sum(bool(item["result_match"]) for item in results)
    average_retries = sum(int(item["retries"]) for item in results) / total if total else 0.0
    failures = [item for item in results if not item["success"]]
    lines = [
        "# Text-to-SQL Evaluation Results", "",
        f"- Run date (UTC): {datetime.now(timezone.utc).isoformat()}",
        f"- Provider/model: {settings.provider} / {settings.effective_model}",
        f"- Questions: {total}",
        f"- Execution success: {successful}/{total} ({successful / total * 100:.1f}%)" if total else "- Execution success: n/a",
        f"- Result matches: {matched}/{total} ({matched / total * 100:.1f}%)" if total else "- Result matches: n/a",
        f"- Average retries: {average_retries:.2f}",
        f"- Failed questions: {len(failures)}", "", "## Per-question results", "",
        "| ID | Executed | Result matched | Retries | Rows |", "|---|---:|---:|---:|---:|",
    ]
    lines.extend([f"| {item['id']} | {'Yes' if item['success'] else 'No'} | {'Yes' if item['result_match'] else 'No'} | {item['retries']} | {item['row_count']} |" for item in results])
    if failures:
        lines.extend(["", "## Failures", ""])
        lines.extend([f"- **{item['id']}**: {item['error']}" for item in failures])
    lines.extend(["", "## Interpretation", "",
                  "Result matching compares the generated query's returned rows with rows from the reference SQL. "
                  "Rows are order-independent for this comparison. This is a small synthetic-data benchmark, "
                  "not evidence of production accuracy.", ""])
    report_path = ROOT / "reports" / "eval_results.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    (ROOT / "reports" / "eval_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nWrote real evaluation results to {report_path}")


if __name__ == "__main__":
    main()
