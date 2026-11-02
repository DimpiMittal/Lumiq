# Lumiq

Lumiq is a local prototype for asking questions about relational data in plain English. It uses an LLM to draft SQL, runs queries against SQLite, PostgreSQL, or MySQL, and displays rows, charts, and an LLM-written summary. CSV files can be imported into SQLite.

## Current status

Implemented: Flask API and browser UI, demo SQLite database, database connection/schema browsing, CSV import, LLM SQL drafting and summaries, SQL editor, basic charts, and browser-local query history.

In progress: SQL safety hardening and a reproducible evaluation foundation. Automated EDA, supervised ML, segmentation, forecasting, RAG, and evaluation dashboard are planned; they are not implemented yet. See [the audit](docs/PROJECT_AUDIT.md) and [roadmap](docs/IMPLEMENTATION_ROADMAP.md).

This is a local portfolio prototype, not a production analytics service. Questions, schema, and result samples are sent to the configured LLM provider. Do not connect sensitive data unless your provider/privacy requirements allow it.

## Run locally

1. Use Python 3.10 or newer.
2. Create and activate a project virtual environment.
3. Install dependencies from `requirements.txt`.
4. Set `GROQ_API_KEY`; optionally set `GEMINI_API_KEY` and a strong `SECRET_KEY`.
5. Run `python app.py` and open `http://127.0.0.1:5000`.

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\requirements.txt
python -m pytest -q
python .\app.py
```

Pytest uses `.pytest-tmp` inside this workspace and disables its cache provider to avoid Windows user-temp/cache permission issues.

The app defaults to loopback binding. PostgreSQL and MySQL drivers are included in requirements; use a dedicated, least-privilege read-only database account. The local SQLite demo database is generated on first startup if absent.

## Project layout

```text
app.py                 Flask routes, providers, database access, SQL policy, CSV ingestion
frontend/              Vanilla JavaScript, HTML page fragments, and CSS
demo.db                Sample SQLite dataset
uploads/               Session CSV data stored as SQLite files
tests/                 SQL safety regression tests
docs/                  Audit, roadmap, architecture, evaluation, and security notes
```

## Tests

Run `python -m pytest -q` and `node --test tests/test_frontend_security.cjs`. SQL parser tests fail explicitly if SQLGlot is not installed; they are not skipped. Install dependencies from `requirements.txt` before expecting SQL execution to work.

## Known limitations

- The project is a single-process prototype. Database connection configs currently live in process memory; use a server-side session/config store before multi-worker deployment.
- SQL results are capped at 500 fetched rows. This is a response cap, not proof that the database did little work.
- The SQL parser dependency must be installed for SQL execution. The project has no offline dependency bundle.
- The UI is not an authenticated multi-user application. Never expose it publicly as-is.
- The LLM summary describes only a small sample of returned rows and must be treated as an interpretation, not authoritative analysis.
- No conventional machine learning or data science pipeline is currently shipped.

## Further reading

- [Project showcase](PROJECT_SHOWCASE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Security](docs/SECURITY.md)
- [LLM evaluation status](docs/LLM_EVALUATION.md)
- [ML pipeline status](docs/ML_PIPELINE.md)
