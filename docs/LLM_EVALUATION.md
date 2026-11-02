# LLM Evaluation Status

## Current status

Lumiq has no benchmark dataset, runner, dashboard, or measured text-to-SQL accuracy. No percentages are reported here. Phase 0's local SQLite/query-safety verification has passed. Phase 1 is planned but has not started. See [IMPLEMENTATION_ROADMAP.md](IMPLEMENTATION_ROADMAP.md) for its plan and scope.

The first benchmark should contain at least 50 hand-reviewed cases covering filters, aggregates, joins, subqueries, dates, ambiguity, unsupported questions, malformed SQL, unauthorized tables, and injection/security attempts. Each case should specify expected behavior and a deterministic result check wherever possible.

## Proposed measurements

- SQL generation and execution success rates.
- Result equivalence against expected outputs, with exact SQL match used only for cases where query form is unambiguous.
- Invalid SQL and unsafe-query rejection rates.
- Clarification behavior on ambiguous questions.
- Latency distribution by provider and query category.
- Error categories such as schema grounding, join logic, aggregation, dialect mismatch, timeout, and unsupported request.

Every run should record dataset version, database fixture, provider/model identifier, prompt/config version, timestamp, latency, and raw outcome while avoiding secrets and private data. Provider comparisons and accuracy claims must come from actual reproducible runs.
