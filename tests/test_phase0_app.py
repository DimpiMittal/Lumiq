import io
import os
import sqlite3
import subprocess
import sys

import pytest

import app


def test_same_origin_session_cookie_and_server_side_database_credentials(monkeypatch):
    def fake_connect(_cfg):
        return sqlite3.connect(":memory:"), "sqlite"

    monkeypatch.setattr(app, "get_conn", fake_connect)
    client = app.app.test_client()
    secret_password = "DO_NOT_PUT_THIS_IN_A_COOKIE"
    response = client.post("/api/connect", json={"config": {
        "type": "mysql", "host": "db.example", "password": secret_password,
    }})
    assert response.status_code == 200
    cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert secret_password not in cookie
    with client.session_transaction() as browser_session:
        ref = browser_session["db_ref"]
    assert app.DB_CONFIGS[ref]["password"] == secret_password


def test_cors_is_not_enabled_for_arbitrary_origins():
    response = app.app.test_client().get("/api/health", headers={"Origin": "https://attacker.example"})
    assert "Access-Control-Allow-Origin" not in response.headers


def test_local_secret_and_cookie_transport_defaults_are_not_legacy_defaults():
    assert app.app.secret_key != "dw-secret-v5"
    assert len(app.app.secret_key) >= 32
    assert app.app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


def test_non_loopback_bind_requires_configured_secret():
    env = os.environ.copy()
    env["HOST"] = "0.0.0.0"
    env["SECRET_KEY"] = ""
    result = subprocess.run(
        [sys.executable, "-c", "import app"], cwd=os.path.dirname(os.path.dirname(__file__)),
        env=env, capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "Set a strong SECRET_KEY" in result.stderr


def test_database_connection_errors_do_not_echo_driver_details(monkeypatch):
    def fail_connect(_cfg):
        raise RuntimeError("password=PRIVATE-DB-PASSWORD")

    monkeypatch.setattr(app, "get_conn", fail_connect)
    response = app.app.test_client().post("/api/connect", json={"config": {"type": "mysql"}})
    assert response.status_code == 400
    assert b"PRIVATE-DB-PASSWORD" not in response.data


def test_csv_upload_normalizes_identifiers_and_handles_values(monkeypatch, tmp_path):
    monkeypatch.setattr(app, "UPL", str(tmp_path))
    client = app.app.test_client()
    response = client.post("/api/upload-csv", data={
        "file": (io.BytesIO(b'"weird""); DROP TABLE x",amount\nhello,12\nworld,3.5\n'), "sales.csv"),
    }, content_type="multipart/form-data")
    assert response.status_code == 200
    body = response.get_json()
    assert body["columns"] == ["weird_DROP_TABLE_x", "amount"]
    assert body["rows"] == 2
    schema = client.get("/api/schema").get_json()["schema"]
    assert body["table"] in schema
    assert schema[body["table"]]["row_count"] == 2


@pytest.mark.parametrize("filename,payload", [
    ("data.txt", b"a\nb\n"),
    ("bad.csv", b"a,b\n1\n"),
    ("empty.csv", b"a,b\n"),
])
def test_csv_upload_rejects_bad_extension_ragged_or_empty_data(monkeypatch, tmp_path, filename, payload):
    monkeypatch.setattr(app, "UPL", str(tmp_path))
    response = app.app.test_client().post("/api/upload-csv", data={
        "file": (io.BytesIO(payload), filename),
    }, content_type="multipart/form-data")
    assert response.status_code == 400


def test_csv_upload_rejects_files_above_request_limit(monkeypatch, tmp_path):
    monkeypatch.setattr(app, "UPL", str(tmp_path))
    payload = b"x" * (app.app.config["MAX_CONTENT_LENGTH"] + 1)
    response = app.app.test_client().post("/api/upload-csv", data={
        "file": (io.BytesIO(payload), "large.csv"),
    }, content_type="multipart/form-data")
    assert response.status_code == 413


def test_demo_sql_and_natural_language_workflow_or_explicit_parser_block(monkeypatch):
    client = app.app.test_client()
    connected = client.post("/api/connect", json={"config": {"type": "sqlite"}})
    assert connected.status_code == 200
    if app.sqlglot is None:
        sql_response = client.post("/api/sql", json={"sql": "SELECT COUNT(*) FROM customers"})
        assert sql_response.status_code == 503
        assert "parser is unavailable" in sql_response.get_json()["error"]
        return
    sql_response = client.post("/api/sql", json={
        "sql": "SELECT city, COUNT(*) AS customers FROM customers GROUP BY city ORDER BY customers DESC LIMIT 3",
    })
    assert sql_response.status_code == 200
    assert sql_response.get_json()["row_count"] == 3

    llm_responses = iter([
        "```sql\nSELECT city, COUNT(*) AS customers FROM customers GROUP BY city ORDER BY customers DESC LIMIT 3\n```",
        "The returned rows show customer counts by city.",
    ])
    monkeypatch.setattr(app, "ai", lambda _messages: next(llm_responses))
    nl_response = client.post("/api/query", json={"question": "How many customers are in each city?"})
    assert nl_response.status_code == 200
    assert nl_response.get_json()["ok"] is True

