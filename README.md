# ✨ Lumiq — Conversational Analytics Platform

<p align="center">
  <strong>Turn natural-language questions into SQL queries, data insights, and visualizations.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Flask-Backend-black?logo=flask" alt="Flask">
  <img src="https://img.shields.io/badge/JavaScript-Frontend-yellow?logo=javascript" alt="JavaScript">
  <img src="https://img.shields.io/badge/LLM-Groq%20%7C%20Gemini-purple" alt="LLM">
  <img src="https://img.shields.io/badge/Status-Prototype-orange" alt="Project Status">
</p>

---

## 📌 Overview

**Lumiq** is a conversational analytics prototype that makes working with relational data more intuitive.

Instead of manually writing SQL queries, users can ask questions about their data in plain English. Lumiq uses Large Language Models (LLMs) to generate SQL queries, executes them against a connected database, and presents the results through structured tables, visualizations, and AI-generated summaries.

The goal is to simplify data exploration and make analytical insights more accessible.

## 🚀 Key Features

| Feature | Description |
|---|---|
| 💬 Natural Language to SQL | Convert business questions into SQL queries using LLMs. |
| 🗄️ Database Connectivity | Database connection code for SQLite, PostgreSQL, and MySQL. |
| 📁 CSV Data Import | Import CSV files into session-specific SQLite databases. |
| 📊 Data Visualization | Explore query results through tables and Chart.js visualizations. |
| 🤖 AI-Powered Summaries | Generate natural-language summaries of query results. |
| ✍️ SQL Editor | Inspect, review, and work with generated SQL queries. |
| 🔍 Schema Exploration | Browse database tables and their available columns. |
| 🕘 Query History | Access previously executed queries using browser-local history. |
| 🔐 SQL Safety Controls | Apply SQL validation and execution safeguards in the local prototype. |

## ⚙️ How It Works

```text
        User's Question
               |
               v
      Natural Language Input
               |
               v
        LLM Integration
        (Groq / Gemini)
               |
               v
        SQL Generation
               |
               v
       SQL Validation
               |
               v
       Database Execution
               |
               v
        Query Results
               |
          +----+----+
          |         |
          v         v
      Visuals    AI Summary
          |         |
          +----+----+
               |
               v
        Analytical Insights
```

## 🛠️ Technology Stack

**Backend**
- Python
- Flask
- REST APIs

**Frontend**
- HTML5
- CSS3
- JavaScript
- Chart.js

**Database**
- SQLite
- PostgreSQL
- MySQL

**Artificial Intelligence**
- Large Language Models (LLMs)
- Groq API
- Google Gemini API
- Prompt Engineering
- Natural Language to SQL

**Development & Testing**
- Git and GitHub
- Pytest
- Node.js test runner
- SQLGlot

## 📂 Project Structure

```text
Lumiq/
│
├── app.py
├── requirements.txt
├── pytest.ini
├── .gitignore
│
├── frontend/
│   ├── index.html
│   ├── css/
│   │   └── main.css
│   ├── js/
│   │   └── app.js
│   └── pages/
│       ├── connect.html
│       ├── dashboard.html
│       ├── history.html
│       ├── query.html
│       ├── settings.html
│       ├── sql.html
│       └── upload.html
│
├── tests/
│   ├── test_phase0_app.py
│   ├── test_sql_safety.py
│   └── test_frontend_security.cjs
│
└── docs/
    ├── ARCHITECTURE.md
    ├── IMPLEMENTATION_ROADMAP.md
    ├── LLM_EVALUATION.md
    ├── ML_PIPELINE.md
    ├── PROJECT_AUDIT.md
    └── SECURITY.md
```

## 💻 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/DimpiMittal/Lumiq.git
cd Lumiq
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Set your API keys in your environment. Never commit actual credentials to GitHub.

Windows PowerShell:

```powershell
$env:GROQ_API_KEY = "your_groq_api_key"
$env:GEMINI_API_KEY = "your_gemini_api_key"
$env:SECRET_KEY = "your_secret_key"
```

Use the provider credentials required by your chosen configuration.

### 5. Run the application

```bash
python app.py
```

Open your browser:

```text
http://127.0.0.1:5000
```

## 🧪 Testing

Run the Python test suite:

```bash
python -m pytest -q
```

On Windows, if the default temporary directory encounters permission issues, use:

```powershell
python -m pytest -q --basetemp "$env:TEMP\lumiq-pytest-temp"
```

Run the frontend security test:

```bash
node --test tests/test_frontend_security.cjs
```

## 🔒 Security & Current Limitations

Lumiq is currently a **local portfolio prototype**, not a production-ready multi-user analytics platform.

Current considerations:

- SQL validation and execution safeguards are implemented, with automated coverage for the local SQLite workflow.
- PostgreSQL and MySQL live integration behavior has not yet been integration-tested.
- The application does not currently provide multi-user authentication.
- Database configurations are maintained in process memory.
- Query results are capped, and AI-generated summaries should be treated as interpretations rather than authoritative conclusions.
- Questions, schema information, and result samples may be sent to the configured LLM provider.

Please use non-sensitive sample data and review provider privacy requirements before connecting external datasets.

## 🗺️ Future Scope

The following are planned enhancements, not currently implemented features:

- [ ] Automated Exploratory Data Analysis (EDA)
- [ ] Supervised Machine Learning workflows
- [ ] Customer segmentation and RFM analysis
- [ ] Time-series forecasting
- [ ] Business-context Retrieval-Augmented Generation (RAG)
- [ ] Reproducible Text-to-SQL evaluation and benchmarking
- [ ] Analytics and model-performance dashboard
- [ ] Improved database configuration and authentication architecture

## 📚 Documentation

For a deeper understanding of the project:

- [Architecture](docs/ARCHITECTURE.md)
- [Security Documentation](docs/SECURITY.md)
- [Project Audit](docs/PROJECT_AUDIT.md)
- [Implementation Roadmap](docs/IMPLEMENTATION_ROADMAP.md)
- [LLM Evaluation Status](docs/LLM_EVALUATION.md)
- [ML Pipeline Status](docs/ML_PIPELINE.md)

## 👩‍💻 Author

**Dimpi Mittal**

BCA — Data Science & Analytics

- GitHub: [@DimpiMittal](https://github.com/DimpiMittal)
- LinkedIn: [Connect with me](https://www.linkedin.com/)

---

<p align="center">
  <strong>Built with curiosity, Python, and AI. ✨</strong>
</p>
