# Lumiq Project Audit

Audit date: 2026-11-01

The findings describe the code at the start of this audit. The first implementation slice below records changes made after that baseline.

## Scope and method

Reviewed the repository tree, `app.py`, `requirements.txt`, the README and showcase document, the shell and JavaScript frontend, and all seven frontend page templates. The workspace contains no Git metadata, test configuration, or test files in the visible project tree. `.env` exists; its contents were intentionally not inspected. No feature was treated as implemented solely because the documentation claims it.

## Existing architecture

Lumiq is a single-process Flask application serving a vanilla HTML/CSS/JavaScript interface. `app.py` contains HTTP routes, provider clients, database adapters, schema discovery, SQL execution, sample-data creation, and CSV ingestion in one module. The browser loads page fragments from `frontend/pages/`, manages navigation and UI state in `frontend/js/app.js`, and calls same-origin `/api/*` endpoints.

For natural-language questions, the backend discovers table/column names and row counts, sends that context and the question to Groq, extracts SQL from free-form model text, executes it, and sends up to ten returned rows to an LLM for a prose summary. The UI renders SQL, results, and a heuristic chart. Groq falls back to Gemini when the first provider call fails. Database connection configuration is stored in Flask's signed client-side session cookie. CSVs are loaded fully into memory and written as a per-session SQLite database under `uploads/`.

## Technology stack found

- Python, Flask, Flask-CORS, requests, python-dotenv
- Optional psycopg2 and PyMySQL drivers
- SQLite standard library
- Plain HTML, CSS, and JavaScript
- Chart.js and Marked loaded from CDNs
- Groq chat completions and Gemini `generateContent` HTTP APIs

Pandas, NumPy, SciPy, scikit-learn, Plotly, SQLAlchemy, SQLGlot, embedding/vector-store packages, Docker, and pytest are not present in the declared requirements or visible implementation.

## Implemented features

- Flask routes for health, connect, schema, natural-language query, SQL query, suggestions, CSV upload, and one-table automatic textual insights.
- Demo SQLite database creation with customers, products, orders, order items, and marketing campaign data when `demo.db` does not already exist.
- SQLite, PostgreSQL, and MySQL connection code and basic table/column/row-count discovery.
- CSV-to-SQLite ingestion with basic type inference from the first row.
- LLM-based SQL drafting, free-text SQL extraction, query execution, LLM-written summaries, and simple chart-type selection.
- Browser-side schema display, query suggestions, results, charts, query replay/history in local storage, theme toggle, and SQL editor.
- A dashboard showing schema/table-size information and some browser-session counters.

## Described but incomplete or not implemented

- The SQL editor does not enforce read-only access robustly; a leading `SELECT` check is not a SQL safety boundary.
- The connection UI says access is secure/read-only and that data never leaves the machine. Those claims are inaccurate for this design: database credentials are placed in a signed but readable client cookie, and schema/question/result samples are sent to external LLM APIs.
- Settings renders API-key fields, but no settings API saves those values. Keys are read from environment variables at process startup.
- Dashboard “insights” and some counters are static/session UI values rather than persistent analytics.
- Automatic insights are LLM-generated text for a sample of one table; there is no statistical profiling or validated EDA pipeline.
- There is no trained ML model, prediction pipeline, customer segmentation, forecasting, RAG/embeddings, model explanation, or benchmarking/evaluation framework.
- No authenticated multi-user data isolation, durable query history, model registry, deployment setup, or operational monitoring is present.

## Code quality and reliability observations

- `app.py` combines unrelated responsibilities, broad exception handling, provider access, and route logic, making changes hard to isolate.
- Database connections are not consistently closed on all error paths. Errors are often returned directly to clients, while provider error strings can contain implementation details.
- Model output is parsed with regular expressions and then executed. A prompt asking for `SELECT` and a `LIMIT` does not enforce either property.
- The SQL endpoint checks only that text begins with `SELECT`; multi-statement/comment/parser edge cases and expensive queries are not controlled.
- The chart assumes the first output column is a label and second is numeric. This can produce misleading charts for arbitrary query results.
- Frontend table rendering inserts returned cell values as HTML without escaping them. AI-generated Markdown is rendered with Marked without sanitization.
- Static page loading inserts fetched HTML directly and does not check HTTP status before presenting it.
- CSV parsing holds the whole upload and all rows in memory, infers types from one sample, and does not robustly normalize or reject duplicate/empty column names or malformed CSVs.
- Browser history stores the user's questions and result metadata in local storage without a retention/privacy control.
- Frontend CDNs are unpinned operational dependencies beyond the versions in the URL; there is no offline asset strategy.
- Many source strings display mojibake in the current PowerShell rendering; source encoding should be verified and corrected as part of polish.

## Security concerns

1. **Arbitrary query execution:** generated SQL is executed without parser validation or database-enforced read-only transactions. SQL editor validation is a regex prefix check.
2. **Credential exposure:** Flask's default session cookie is signed, not encrypted. Storing PostgreSQL/MySQL passwords in the session exposes them to its holder. The fallback secret is hard-coded and predictable.
3. **Cross-origin policy:** CORS is configured for all origins with credentials support, which is an unsafe combination for a credentialed application.
4. **Network exposure:** Flask binds to `0.0.0.0`; the app is reachable on interfaces and has no authentication or CSRF protection.
5. **Data exfiltration:** schema, questions, and result samples are sent to third-party LLM services. The UI's local-only privacy statement is therefore false.
6. **XSS:** database result cells are not escaped in `buildTable`; rendered Markdown is not sanitized. Database values or model output can become executable markup.
7. **Resource exhaustion:** no upload size limit, row/column limit, execution timeout, rate limit, or result-size bound is enforced on the backend.
8. **File handling:** CSV-derived names and headers are interpolated into SQL identifiers with incomplete validation/escaping; per-session upload files have no cleanup lifecycle.
9. **Information leakage:** API error responses often include raw exception text; health exposes configured-provider presence (not keys, but still operational state).

## Data handling limitations

- Schema discovery counts every row in every table on connection/schema requests, which can be costly.
- Foreign keys/relationships are not retrieved, and schema descriptions/business definitions are absent.
- PostgreSQL schema discovery is limited to `public`; identifier quoting and dialect handling are incomplete.
- SQL results have no universal server-side row/byte cap and database-specific timeout controls.
- CSV type detection uses only the first row and inserts records one by one; it does not validate headers, null semantics, encoding quality, or inconsistent rows.
- The sample dataset is small synthetic demo data. It supports UI and basic SQL demonstrations, not robust DS/ML evaluation.

## AI/LLM limitations

- No structured-output/schema validation, clarification workflow, conversation context, prompt-injection defenses, retry policy for SQL errors, or provider-specific telemetry.
- The LLM sees a flat schema summary without FK relationships or business context.
- SQL is extracted by regex; output with comments, multiple statements, unsupported dialect syntax, or unsafe constructs can pass to execution.
- Gemini fallback converts chat messages into a single plain prompt, losing role structure.
- The summary model sees at most ten rows but is told the total count; this can encourage unsupported generalizations.
- There is no benchmark dataset, reproducible provider comparison, latency/cost tracking, failure taxonomy, or regression gate.
- LLM output is not calibrated and no claim-level evidence is linked to source rows or aggregates.

## Test and deployment status

No automated tests, test configuration, CI workflow, Dockerfile, lockfile, or deployment configuration were found in the visible project. The audit did not run a test suite because none exists. The current app is suitable as a local prototype after safety fixes, not as an internet-facing service.

## First implementation slice status

After the baseline review, the project added SQLGlot AST validation, SQLite authorizer checks and query deadlines, PostgreSQL/MySQL read-only and timeout settings, a SQL-level 500-row cap, a 10 MiB request limit, loopback binding, safer cookie defaults, process-local database config references, generic error responses, and escaped schema/dashboard/table/summary output. CORS wildcard support was removed. CSV header names are normalized and bounded, malformed rows are rejected, and inserts are parameterized. The connection screen now discloses LLM data processing.

The SQLGlot issue was reproduced with 30.27.0 in `E:\Lumiq\.venv`: SQLGlot parsed `SELECT FROM customers` into an `exp.Select` with zero projection expressions, despite `ErrorLevel.RAISE`. Validation now checks every Select node in the AST for at least one projection, covering nested CTEs and subqueries; regression cases verify malformed forms reject while valid SELECTs, joins, CTEs, subqueries, and UNIONs pass.

The CSV temp-directory failure was addressed in `pytest.ini`: pytest disables its cache provider and uses the workspace-local `.pytest-tmp` basetemp. CSV tests and assertions remain. Latest run: `& .\\.venv\\Scripts\\python.exe -m pytest -q` reports **47 passed, 0 failed, 0 errors, 0 skipped, 0 warnings**. The separate Node rendering test reports **1 passed**; syntax checks pass. Demo SQL editor execution and the mocked text-to-SQL flow are exercised end to end against `demo.db`.

No PostgreSQL or MySQL server was available, and no database endpoint credentials/configuration were supplied for live integration tests. Their configured read-only/timeout behavior is not verified. No real external LLM request was made. Phase 0 is complete for the verified local SQLite/query-safety scope; do not claim production readiness or verified PostgreSQL/MySQL enforcement. Public deployment additionally requires auth, CSRF, rate limits, and config-store lifecycle controls.

## Recommended architecture

Preserve Flask and the current UI initially, but separate code into small modules: configuration, database adapters/schema catalog, SQL policy/execution, LLM provider clients and text-to-SQL service, data profiling/EDA, ML workflows, evaluation, and API routes. Use explicit request/response schemas and one error-handling boundary. Keep database credentials server-side (or use a deliberately local-only connection design), enforce read-only execution at both parser and database layers, and keep expensive analytics behind bounded services. Add reproducible evaluation and tests before claiming improved accuracy. Add EDA and conventional ML as independent, measurable modules rather than implying the LLM itself is ML training.

## Prioritized recommendations

1. Establish baseline tests and a reproducible 50+ case text-to-SQL/security benchmark before changing model prompts.
2. Fix execution safety: SQL parsing, single read-only statement allowlist, table allowlist, backend row/time/resource caps, safe database roles/transactions, and credential handling.
3. Correct XSS and privacy claims; bound and validate CSV ingestion and avoid returning raw internal errors.
4. Extract database and LLM services from `app.py`; add structured schema metadata including foreign keys and business glossary.
5. Add LLM evaluation with real measured results and an error-analysis report.
6. Add deterministic EDA with pandas/numpy/scipy and tests for profiling/statistics.
7. Add ML workflows (baselines, leakage-safe splits, pipelines, metrics, serialization) after defining usable datasets and suitability checks.
8. Add RFM segmentation and forecasting only when data prerequisites are met and baseline comparisons are available.
9. Add dashboards/UI affordances for the implemented services, then document setup/deployment and known limitations.

