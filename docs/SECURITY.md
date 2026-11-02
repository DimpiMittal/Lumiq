# Security status and Phase 0 verification

## Implemented safeguards

- Same-origin API; no permissive CORS configuration is enabled.
- Session cookie is HttpOnly and SameSite=Lax. The local fallback secret is random per process. A configured `SECRET_KEY` must be at least 32 characters; a non-loopback bind requires a configured key. Cookies are Secure for non-loopback binds or when `COOKIE_SECURE=true`.
- Database credentials are kept in a process-local map and the signed cookie contains only a random reference.
- Request bodies are limited to 10 MiB. CSV ingestion validates `.csv` filename extension, UTF-8, header/row widths, at most 200 columns, 50,000 rows, and 1,000,000 cells. Column/table names are normalized and inserted values are parameterized.
- SQLGlot is intended to parse one dialect-specific query, allow only query ASTs, reject table references outside discovered names, reject qualified names, `SELECT INTO`, locking reads, and selected dangerous functions, and apply a 500-row SQL cap.
- SQLite adds a read-only authorizer and a five-second progress-handler deadline. PostgreSQL is configured read-only with a five-second statement timeout. MySQL is configured with a read-only transaction default and a five-second maximum execution time.
- Database-derived schema labels, dashboard table names, result cells, questions, errors, SQL, and summaries are escaped or emitted as text before rendering.
- The default bind address is loopback. Error responses avoid returning raw provider/driver exception strings in the main query/connect routes.

## Verification status (2026-11-01)

SQLGlot 30.27.0 is installed in and was tested with Lumiq's `E:\Lumiq\.venv` (Python 3.12). The validator now rejects SQLGlot's incomplete `Select` ASTs when any SELECT node, including nested CTE/subquery nodes, has no projection expressions. Valid SELECT, JOIN, CTE, subquery, and UNION cases pass. The earlier missing-dependency installation blocker is resolved in this environment.

Pytest is configured in `pytest.ini` to disable the cache provider and place its basetemp at `.pytest-tmp` under the workspace. This avoids the Windows user-temp permission failure while preserving all CSV tests and assertions. Latest verification using `& .\\.venv\\Scripts\\python.exe -m pytest -q`:

- **47 passed, 0 failed, 0 errors, 0 skipped, 0 warnings**.
- This includes SQL mutation/malformed/stacked/table-allowlist tests; SQL row-limit and SQLite timeout/authorizer tests; CSV upload limits and identifier handling; and the demo SQL plus mocked text-to-SQL end-to-end flow.
- `node --check frontend/js/app.js`: passed. `node --test tests/test_frontend_security.cjs`: **1 passed, 0 failed**.
- PostgreSQL/MySQL driver code is covered by parser/dialect unit cases, but no live PostgreSQL/MySQL servers or connection settings were available. Their transaction read-only and timeout behavior remains **unverified against actual servers**. No external LLM provider call was made; the end-to-end LLM response was mocked.

Phase 0's locally testable SQLite/query-safety scope is complete. This does not mean production readiness, nor does it verify PostgreSQL/MySQL integration.

## Remaining risks

- No authentication, CSRF protection, rate limiting, or robust multi-user isolation. Keep this prototype local.
- The process-local config map is single-process only and has no expiry/cleanup; stale credentials remain in memory until restart.
- Database transaction settings are defense in depth, not a substitute for least-privilege read-only DB users. MySQL/PostgreSQL behavior still needs live verification.
- The five-second SQLite progress callback bounds VM execution time approximately; metadata discovery/table row counts are outside that callback. Timeouts are not a hard resource sandbox.
- SQL allowlisting does not make arbitrary permitted `SELECT` expressions harmless. DB functions, views, row-level permissions, and provider data exposure require careful DB configuration. The app sends question/schema/result samples to the configured LLM provider.
- CSV upload is bounded but still buffers the file and rows in process memory. Per-session SQLite files and process-map entries are not cleaned up. Invalid or duplicate input is handled, but disk quota and retention controls are absent.
- Some routes outside the main connection/query handlers still need a full error-response and connection-lifecycle review. No production WSGI/deployment or security review exists.
- Schema-qualified SQL (for example `main.customers` or `public.customers`) is rejected by policy. Use unqualified discovered table names in the current SQL editor.

## Before public deployment

Add authentication/authorization and CSRF defenses, a lifecycle-managed server-side session store, upload cleanup/quotas, rate/resource limits, production WSGI/TLS, least-privilege DB credentials, redacted logs, provider data-processing controls, a complete security regression suite, and a deployment security review. Do not claim production readiness until those controls and operational tests exist.
