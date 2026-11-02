# Lumiq — Project Showcase

## Portfolio description

Lumiq is a local conversational analytics prototype built with Flask and vanilla JavaScript. Users connect a relational database or upload a CSV, ask a business question in plain English, inspect the generated SQL, and view query results with a chart and an LLM-written summary. The app currently supports SQLite, PostgreSQL, and MySQL connection code, plus Groq/Gemini provider calls.

## What is implemented

- End-to-end browser-to-Flask workflow for questions, SQL execution, and results.
- Demo relational dataset and basic schema/table browsing.
- CSV import into a session-specific SQLite file.
- LLM-based SQL drafting, suggestions, and result summaries.
- SQL editor, result tables, Chart.js charts, and browser-local query history.
- SQL safety for the local SQLite flow is tested: SQLGlot AST validation, SQLite authorizer/deadline, result cap, and validation for SQLite/PostgreSQL/MySQL dialect SQL. Live PostgreSQL/MySQL transaction enforcement remains unverified.

## Honest technical status

This is still a prototype. The database config store is process-local, the application has no authentication, and no measured text-to-SQL accuracy is available. The latest Python suite reports **47 passed** in Lumiq's `.venv`, including legitimate demo SQL and mocked text-to-SQL flows. PostgreSQL/MySQL behavior has not been integration-tested. Do not describe this as production-ready or claim trained ML/DS capabilities.

Automated EDA, conventional supervised ML, RFM segmentation, forecasting, business-context RAG, and a performance dashboard are roadmap items, not delivered features. The current LLM integration uses pretrained APIs; it does not train a model.

## Interview version

> I built Lumiq, a Flask-based analytics prototype that turns natural-language business questions into inspectable SQL and visualized query results. It supports CSV ingestion and relational database connections, with an LLM-assisted workflow. I am strengthening it with execution safeguards and a reproducible text-to-SQL benchmark before making accuracy or production-readiness claims.

## Demo notes

Run the local setup in [README.md](README.md), use the built-in demo data, and show a question whose SQL and returned rows can be verified in the SQL editor. Keep API keys in environment configuration and use non-sensitive sample data.
