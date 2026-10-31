
"""Paced evaluation of the Text-to-SQL agent with provider retry handling."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import Settings
from app.executor import QueryExecutionError, execute_read_only
from app.llm import LLMClient, LLMConfigurationError, LLMProviderError
from app.schema import get_schema_description
from app.sql_guard import validate_select_only

ROOT = Path(__file__).resolve().parents[1]
MAX_PROVIDER_ATTEMPTS = 3


def normalize_value(value: Any) -> tuple[str, Any]:
    """Normalize values without depending on SQL column aliases."""
    if isinstance(value, bool):
        return ("boolean", value)

    if isinstance(value, (int, float)):
        return ("number", round(float(value), 2))

    if value is None:
        return ("null", None)

    return ("text", str(value))


def canonical_row(row: dict[str, Any]) -> tuple:
    """Create an alias-independent signature for one result row."""
    values = [normalize_value(value) for value in row.values()]
    return tuple(
        sorted(values, key=lambda value: json.dumps(value, sort_keys=True))
    )


def canonical(rows: list[dict[str, Any]]) -> list[tuple]:
    """Compare rows without requiring a particular output order."""
    signatures = [canonical_row(row) for row in rows]
    return sorted(
        signatures,
        key=lambda value: json.dumps(value, sort_keys=True),
    )


def results_match(
    actual: list[dict[str, Any]],
    expected: list[dict[str, Any]],
    actual_truncated: bool,
    expected_truncated: bool,
) -> bool:
    """Compare result values, not SQL aliases."""
    return (
        actual_truncated == expected_truncated
        and canonical(actual) == canonical(expected)
    )


def write_reports(
    results: list[dict[str, Any]],
    total_questions: int,
    settings: Settings,
) -> None:
    """Save benchmark results, including partial failures."""
    attempted = len(results)
    successful = sum(bool(item["success"]) for item in results)
    matched = sum(bool(item["result_match"]) for item in results)

    average_retries = (
        sum(int(item["retries"]) for item in results) / attempted
        if attempted
        else 0.0
    )

    overall_accuracy = (
        matched / attempted * 100 if attempted else 0.0
    )

    successful_accuracy = (
        matched / successful * 100 if successful else 0.0
    )

    lines = [
        "# Text-to-SQL Evaluation Results",
        "",
        f"- Run date (UTC): {datetime.now(timezone.utc).isoformat()}",
        f"- Provider/model: {settings.provider} / {settings.effective_model}",
        f"- Total benchmark questions: {total_questions}",
        f"- Questions attempted: {attempted}/{total_questions}",
        f"- Successful executions: {successful}/{attempted}",
        f"- Correct result matches: {matched}/{attempted}",
        f"- Overall benchmark accuracy: {overall_accuracy:.2f}%",
        f"- Accuracy among successful executions: {successful_accuracy:.2f}%",
        f"- Average provider retries: {average_retries:.2f}",
        "- Evaluation mode: one successful SQL-generation response per question, with up to three provider attempts",
        "- Answer generation excluded to reduce API consumption",
        "- SQL aliases and output row ordering ignored during comparison",
        "- Numeric values rounded to two decimal places for comparison",
        "",
        "## Per-question results",
        "",
        "| ID | Executed | Result matched | Retries | Rows |",
        "|---|---:|---:|---:|---:|",
    ]

    for item in results:
        lines.append(
            f"| {item['id']} | "
            f"{'Yes' if item['success'] else 'No'} | "
            f"{'Yes' if item['result_match'] else 'No'} | "
            f"{item['retries']} | {item['row_count']} |"
        )

    failures = [
        item for item in results
        if not item["success"] or not item["result_match"]
    ]

    if failures:
        lines.extend(["", "## Failures and mismatches", ""])
        for item in failures:
            reason = item["error"] or "Generated SQL returned different results"
            lines.append(f"- **{item['id']}**: {reason}")

    lines.extend([
        "",
        "## Interpretation",
        "",
        "This is a small benchmark using synthetic pharmaceutical data. "
        "It measures SQL generation, validation and execution. "
        "It does not establish production accuracy or generalization.",
        "",
    ])

    reports_dir = ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    (reports_dir / "eval_results.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    (reports_dir / "eval_results.json").write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )


def is_transient_provider_error(error: Exception) -> bool:
    """Identify provider errors that may succeed on another attempt."""
    message = str(error).lower()

    transient_phrases = (
        "network request failed",
        "server disconnected",
        "timed out",
        "returned an empty response",
        "timeout",
        "temporarily unavailable",
        "connection reset",
        "connection refused",
        "api error 429",
        "api error 500",
        "api error 502",
        "api error 503",
        "api error 504",
    )

    return any(phrase in message for phrase in transient_phrases)


def main() -> None:
    settings = Settings.from_env()
    llm = LLMClient(settings)

    dataset = json.loads(
        (ROOT / "evaluation" / "questions.json").read_text(
            encoding="utf-8"
        )
    )

    schema = get_schema_description(
        settings.database_path,
        sample_rows=0,
    )

    request_interval = max(
        13.0,
        float(os.getenv("EVAL_REQUEST_INTERVAL_SECONDS", "13")),
    )

    last_request_time: float | None = None
    results: list[dict[str, Any]] = []

    for item in dataset:
        question_id = item["id"]
        question = item["question"]

        record: dict[str, Any] = {
            "id": question_id,
            "question": question,
            "success": False,
            "result_match": False,
            "retries": 0,
            "row_count": 0,
            "sql": None,
            "error": None,
        }

        generated_sql: str | None = None

        # Attempt SQL generation up to three times for transient errors.
        for attempt in range(MAX_PROVIDER_ATTEMPTS):
            if last_request_time is not None:
                elapsed = time.monotonic() - last_request_time
                wait_seconds = request_interval - elapsed

                if wait_seconds > 0:
                    print(
                        f"Waiting {wait_seconds:.1f}s before the next API request..."
                    )
                    time.sleep(wait_seconds)

            last_request_time = time.monotonic()

            try:
                generated_sql = llm.generate_sql(question, schema)
                break

            except LLMConfigurationError as error:
                record["error"] = str(error)
                break

            except LLMProviderError as error:
                record["error"] = str(error)

                if (
                    is_transient_provider_error(error)
                    and attempt < MAX_PROVIDER_ATTEMPTS - 1
                ):
                    record["retries"] += 1
                    print(
                        f"{question_id}: temporary provider error. "
                        f"Retry {record['retries']}/"
                        f"{MAX_PROVIDER_ATTEMPTS - 1}."
                    )
                    continue

                break

        if generated_sql is None:
            results.append(record)
            print(
                f"{question_id}: success=False "
                f"result_match=False retries={record['retries']} "
                f"error={record['error']}"
            )
            continue

        try:
            validation = validate_select_only(
                generated_sql,
                settings.max_query_rows,
            )

            if not validation.valid or not validation.sql:
                record["error"] = (
                    validation.error or "SQL validation failed"
                )
            else:
                actual_rows, actual_truncated = execute_read_only(
                    validation.sql,
                    settings.database_path,
                    max_rows=settings.max_query_rows,
                    timeout_seconds=settings.query_timeout_seconds,
                )

                expected_rows, expected_truncated = execute_read_only(
                    item["expected_sql"],
                    settings.database_path,
                    max_rows=settings.max_query_rows,
                    timeout_seconds=settings.query_timeout_seconds,
                )

                record.update({
                    "success": True,
                    "result_match": results_match(
                        actual_rows,
                        expected_rows,
                        actual_truncated,
                        expected_truncated,
                    ),
                    "row_count": len(actual_rows),
                    "sql": validation.sql,
                })

        except (QueryExecutionError, ValueError) as error:
            record["error"] = str(error)

        results.append(record)

        print(
            f"{question_id}: "
            f"success={record['success']} "
            f"result_match={record['result_match']} "
            f"retries={record['retries']}"
        )

    write_reports(
        results,
        len(dataset),
        settings,
    )

    successful = sum(bool(item["success"]) for item in results)
    matched = sum(bool(item["result_match"]) for item in results)

    print(
        f"\nEvaluation finished: {len(results)}/{len(dataset)} "
        "questions attempted."
    )
    print(f"Successful executions: {successful}/{len(dataset)}")
    print(f"Correct result matches: {matched}/{len(dataset)}")
    print("Wrote reports/eval_results.md")
    print("Wrote reports/eval_results.json")


if __name__ == "__main__":
    main()