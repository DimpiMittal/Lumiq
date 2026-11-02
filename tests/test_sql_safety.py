import itertools
import sqlite3

import pytest

import app


@pytest.fixture
def require_sqlglot():
    if app.sqlglot is None:
        pytest.fail("SQL SAFETY BLOCKED: install sqlglot from requirements.txt; parser tests must not be skipped")


@pytest.mark.parametrize("sql", [
    "SELECT city, COUNT(*) AS n FROM customers GROUP BY city ORDER BY n DESC",
    "SELECT * FROM customers WHERE city = 'Pune' -- a harmless comment",
    "WITH recent AS (SELECT * FROM orders) SELECT COUNT(*) FROM recent",
    "SELECT * FROM customers WHERE id IN (SELECT customer_id FROM orders)",
    "SELECT c.id, o.id FROM customers c JOIN orders o ON c.id = o.customer_id",
    "WITH recent AS (SELECT id, customer_id FROM orders) SELECT c.id FROM customers c JOIN recent r ON c.id = r.customer_id",
    "SELECT city FROM customers UNION SELECT category FROM products",
])
def test_accepts_read_queries_ctes_subqueries_unions_and_comments(require_sqlglot, sql):
    result = app.validate_read_query(sql, "sqlite", {"customers", "orders", "products"})
    assert result


@pytest.mark.parametrize("sql", [
    "INSERT INTO customers VALUES (1)",
    "UPDATE customers SET city='X'",
    "DELETE FROM customers",
    "DROP TABLE customers",
    "ALTER TABLE customers ADD COLUMN x TEXT",
    "CREATE TABLE x (id INTEGER)",
    "PRAGMA table_info(customers)",
    "ATTACH DATABASE 'x.db' AS x",
    "SELECT * INTO archive FROM customers",
    "SELECT * FROM customers FOR UPDATE",
    "SELECT pg_read_file('/etc/passwd')",
    "SELECT LOAD_FILE('/etc/passwd')",
    "SELECT SLEEP(60)",
    "SELECT BENCHMARK(10000000, SHA2('x', 256))",
    "SELECT * FROM customers; -- split\nDELETE FROM customers",
    "SELECT * FROM customers; DROP TABLE customers",
    "SELECT FROM customers",
    "SELECT",
    "SELECT * FROM customers WHERE id IN (SELECT FROM orders)",
    "WITH recent AS (SELECT FROM orders) SELECT id FROM recent",
    "SELECT * FROM private_table",
    "SELECT * FROM main.customers",
])
def test_rejects_mutations_stacked_malformed_and_unauthorized_sql(require_sqlglot, sql):
    with pytest.raises(ValueError):
        app.validate_read_query(sql, "sqlite", {"customers"})


@pytest.mark.parametrize("db_type,dialect", [
    ("sqlite", "sqlite"), ("postgresql", "postgres"), ("mysql", "mysql"),
])
def test_validates_and_limits_each_supported_dialect(require_sqlglot, db_type, dialect):
    sql = app.validate_read_query("SELECT * FROM customers", db_type, {"customers"})
    parsed = app.sqlglot.parse(sql, read=dialect)
    assert len(parsed) == 1
    assert parsed[0].args.get("limit").expression.this == "500"


def test_clamps_unbounded_limit_and_preserves_smaller_limit(require_sqlglot):
    capped = app.validate_read_query("SELECT * FROM customers LIMIT 50000", "sqlite", {"customers"})
    smaller = app.validate_read_query("SELECT * FROM customers LIMIT 3", "sqlite", {"customers"})
    assert "LIMIT 500" in capped.upper()
    assert "LIMIT 3" in smaller.upper()


def test_sqlite_authorizer_blocks_writes_if_parser_is_bypassed(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE customers (id INTEGER)")
    conn.execute("INSERT INTO customers VALUES (1)")
    monkeypatch.setattr(app, "validate_read_query", lambda sql, dbt, tables: sql)
    with pytest.raises(sqlite3.DatabaseError):
        app.run_sql(conn, "sqlite", "DELETE FROM customers", {"customers"})
    assert conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 1
    conn.close()


def test_sqlite_result_limit_is_enforced_in_sql_and_response(require_sqlglot):
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE customers (id INTEGER)")
    conn.executemany("INSERT INTO customers VALUES (?)", ((n,) for n in range(600)))
    rows, columns = app.run_sql(conn, "sqlite", "SELECT id FROM customers", {"customers"})
    assert columns == ["id"]
    assert len(rows) == app.MAX_QUERY_ROWS
    conn.close()


def test_sqlite_query_deadline_interrupts_expensive_query(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.executescript("CREATE TABLE a (x); CREATE TABLE b (x);")
    conn.executemany("INSERT INTO a VALUES (?)", ((n,) for n in range(1000)))
    conn.executemany("INSERT INTO b VALUES (?)", ((n,) for n in range(1000)))
    ticks = itertools.chain([0.0, 6.0], itertools.repeat(6.0))
    monkeypatch.setattr(app.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(app, "validate_read_query", lambda sql, dbt, tables: sql)
    with pytest.raises(sqlite3.OperationalError, match="interrupted"):
        app.run_sql(conn, "sqlite", "SELECT COUNT(*) FROM a CROSS JOIN b", {"a", "b"})
    conn.close()
