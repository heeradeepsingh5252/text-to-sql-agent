# Text-to-SQL Evaluation Results

- Run date (UTC): 2026-10-31T06:31:02.877691+00:00
- Provider/model: groq / openai/gpt-oss-20b
- Total benchmark questions: 20
- Questions attempted: 20/20
- Successful executions: 20/20
- Correct result matches: 20/20
- Overall benchmark accuracy: 100.00%
- Accuracy among successful executions: 100.00%
- Average provider retries: 0.00
- Evaluation mode: one successful SQL-generation response per question, with up to three provider attempts
- Answer generation excluded to reduce API consumption
- SQL aliases and output row ordering ignored during comparison
- Numeric values rounded to two decimal places for comparison

## Per-question results

| ID | Executed | Result matched | Retries | Rows |
|---|---:|---:|---:|---:|
| Q01 | Yes | Yes | 0 | 1 |
| Q02 | Yes | Yes | 0 | 8 |
| Q03 | Yes | Yes | 0 | 1 |
| Q04 | Yes | Yes | 0 | 1 |
| Q05 | Yes | Yes | 0 | 4 |
| Q06 | Yes | Yes | 0 | 1 |
| Q07 | Yes | Yes | 0 | 4 |
| Q08 | Yes | Yes | 0 | 1 |
| Q09 | Yes | Yes | 0 | 8 |
| Q10 | Yes | Yes | 0 | 12 |
| Q11 | Yes | Yes | 0 | 1 |
| Q12 | Yes | Yes | 0 | 5 |
| Q13 | Yes | Yes | 0 | 1 |
| Q14 | Yes | Yes | 0 | 28 |
| Q15 | Yes | Yes | 0 | 4 |
| Q16 | Yes | Yes | 0 | 1 |
| Q17 | Yes | Yes | 0 | 3 |
| Q18 | Yes | Yes | 0 | 1 |
| Q19 | Yes | Yes | 0 | 4 |
| Q20 | Yes | Yes | 0 | 2 |

## Interpretation

This is a small benchmark using synthetic pharmaceutical data. It measures SQL generation, validation and execution. It does not establish production accuracy or generalization.
