"""
DataWise AI — v5
Run: python app.py  →  open http://localhost:5000
"""
import os, re, json, sqlite3, traceback, csv, io, hashlib, time
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

import requests
from flask import Flask, request, jsonify, session, send_from_directory
try:
    import sqlglot
    from sqlglot import exp
except ImportError:
    sqlglot = None
    exp = None

try: import psycopg2; HAS_PG = True
except: HAS_PG = False
try: import pymysql; HAS_MY = True
except: HAS_MY = False

BASE   = os.path.dirname(os.path.abspath(__file__))
FRONT  = os.path.join(BASE, "frontend")
DEMO   = os.path.join(BASE, "demo.db")
UPL    = os.path.join(BASE, "uploads")
os.makedirs(UPL, exist_ok=True)

HOST = os.environ.get("HOST", "127.0.0.1")
CONFIGURED_SECRET = os.environ.get("SECRET_KEY")
if CONFIGURED_SECRET and len(CONFIGURED_SECRET) < 32:
    raise RuntimeError("SECRET_KEY must be at least 32 characters.")
if HOST not in {"127.0.0.1", "localhost", "::1"} and not CONFIGURED_SECRET:
    raise RuntimeError("Set a strong SECRET_KEY before binding Lumiq beyond loopback.")
app = Flask(__name__, static_folder=FRONT, static_url_path="")
app.secret_key = CONFIGURED_SECRET or os.urandom(32)
app.config.update(MAX_CONTENT_LENGTH=10 * 1024 * 1024,
                  SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  SESSION_COOKIE_SECURE=(HOST not in {"127.0.0.1", "localhost", "::1"}
                      or os.environ.get("COOKIE_SECURE", "").lower() in {"1", "true", "yes"}))
DB_CONFIGS = {}  # Process-local prototype store, so DB passwords stay out of cookies.

GROQ_KEY   = os.environ.get("GROQ_API_KEY", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_QUERY_ROWS = 500
QUERY_TIMEOUT_SECONDS = 5

def session_db_config():
    return DB_CONFIGS.get(session.get("db_ref"), {"type":"sqlite"})

class SQLSafetyDependencyError(RuntimeError):
    pass

# ── Serve frontend pages ───────────────────────────────────────────────────────
@app.route("/")
def root(): return send_from_directory(FRONT, "index.html")

@app.route("/<path:path>")
def static_proxy(path):
    full = os.path.join(FRONT, path)
    if os.path.isfile(full): return send_from_directory(FRONT, path)
    return send_from_directory(FRONT, "index.html")

# ── AI ─────────────────────────────────────────────────────────────────────────
def call_groq(msgs):
    if not GROQ_KEY: return None, "no key"
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={"model": GROQ_MODEL, "messages": msgs, "temperature": 0.1, "max_tokens": 2048},
            timeout=30)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"], None
    except Exception: return None, "Groq request failed"

def call_gemini(prompt):
    if not GEMINI_KEY: return None, "no key"
    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}",
            json={"contents":[{"parts":[{"text":prompt}]}]}, timeout=30)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"], None
    except Exception: return None, "Gemini request failed"

def ai(msgs):
    t, e1 = call_groq(msgs)
    if t: return t
    t, e2 = call_gemini("\n".join(m["content"] for m in msgs))
    if t: return t
    raise RuntimeError("Configured LLM providers are unavailable.")

# ── DB ─────────────────────────────────────────────────────────────────────────
def get_conn(cfg):
    t = cfg.get("type","sqlite")
    if t == "sqlite":
        path = cfg.get("path") or DEMO
        c = sqlite3.connect(path, check_same_thread=False)
        c.row_factory = sqlite3.Row
        return c, "sqlite"
    if t == "postgresql":
        if not HAS_PG: raise RuntimeError("pip install psycopg2-binary")
        conn=psycopg2.connect(host=cfg["host"],port=cfg.get("port",5432),
            database=cfg["database"],user=cfg["username"],password=cfg["password"],connect_timeout=10)
        conn.set_session(readonly=True)
        with conn.cursor() as cur: cur.execute("SET SESSION statement_timeout = '5000ms'")
        return conn, "postgresql"
    if t == "mysql":
        if not HAS_MY: raise RuntimeError("pip install pymysql")
        conn=pymysql.connect(host=cfg["host"],port=int(cfg.get("port",3306)),
            database=cfg["database"],user=cfg["username"],password=cfg["password"],
            connect_timeout=10,cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            cur.execute("SET SESSION TRANSACTION READ ONLY")
            cur.execute("SET SESSION MAX_EXECUTION_TIME=5000")
        return conn, "mysql"
    raise ValueError(f"Unknown: {t}")

def get_schema(conn, dbt):
    schema={}; cur=conn.cursor()
    try:
        if dbt=="sqlite":
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            for (n,) in cur.fetchall():
                ident='"'+n.replace('"','""')+'"'
                cur.execute(f"PRAGMA table_info({ident})")
                cols=[{"name":c[1],"type":c[2]} for c in cur.fetchall()]
                cur.execute(f"SELECT COUNT(*) FROM {ident}")
                schema[n]={"columns":cols,"row_count":cur.fetchone()[0]}
        elif dbt=="postgresql":
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
            for (n,) in cur.fetchall():
                cur.execute("SELECT column_name,data_type FROM information_schema.columns WHERE table_name=%s",(n,))
                cols=[{"name":r[0],"type":r[1]} for r in cur.fetchall()]
                ident='"'+n.replace('"','""')+'"'
                cur.execute(f'SELECT COUNT(*) FROM {ident}')
                schema[n]={"columns":cols,"row_count":cur.fetchone()[0]}
        elif dbt=="mysql":
            cur.execute("SHOW TABLES")
            for row in cur.fetchall():
                n=list(row.values())[0]
                ident='`'+n.replace('`','``')+'`'
                cur.execute(f"DESCRIBE {ident}")
                cols=[{"name":r["Field"],"type":r["Type"]} for r in cur.fetchall()]
                cur.execute(f"SELECT COUNT(*) AS c FROM {ident}")
                schema[n]={"columns":cols,"row_count":list(cur.fetchone().values())[0]}
    except Exception as exc:
        raise RuntimeError("Could not read database schema.") from exc
    return schema

def validate_read_query(sql, dbt, allowed_tables):
    """Fail closed unless SQL parses as one read-only query over known tables."""
    if sqlglot is None:
        raise SQLSafetyDependencyError("SQL safety parser is unavailable.")
    dialect={"sqlite":"sqlite", "postgresql":"postgres", "mysql":"mysql"}[dbt]
    try:
        parsed=sqlglot.parse(sql, read=dialect, error_level=sqlglot.ErrorLevel.RAISE)
    except sqlglot.errors.ParseError as exc:
        raise ValueError("The query could not be parsed for this database.") from exc
    if len(parsed)!=1 or parsed[0] is None or not isinstance(parsed[0], exp.Query):
        raise ValueError("Only one read-only SELECT query is allowed.")
    query=parsed[0]
    # SQLGlot is intentionally permissive for some incomplete SELECT forms.
    # Check every SELECT node (including CTEs and nested queries) has a projection.
    selects=list(query.find_all(exp.Select))
    if not selects or any(not select.expressions for select in selects):
        raise ValueError("Every SELECT must contain at least one projection expression.")
    if query.find(exp.Into) or query.find(exp.Lock):
        raise ValueError("Locking or SELECT INTO clauses are not allowed.")
    blocked_functions={"load_extension","pg_read_file","pg_read_binary_file","pg_sleep",
                       "pg_advisory_lock","pg_advisory_xact_lock","load_file","sleep",
                       "benchmark","get_lock","release_lock"}
    if any(getattr(func,"name","").casefold() in blocked_functions
           for func in query.find_all(exp.Anonymous)):
        raise ValueError("This SQL function is not allowed.")
    cte_names={cte.alias_or_name.casefold() for cte in query.find_all(exp.CTE)}
    tables=list(query.find_all(exp.Table))
    if any(table.db or table.catalog for table in tables):
        raise ValueError("Qualified table names are not allowed.")
    names={table.name.casefold() for table in tables}-cte_names
    allowed={str(name).casefold() for name in allowed_tables}
    if names-allowed:
        raise ValueError("The query references a table that is not available.")
    current_limit=query.args.get("limit")
    current_value=current_limit.args.get("expression") if current_limit else None
    if current_limit:
        if not isinstance(current_value, exp.Literal) or not current_value.is_number:
            raise ValueError("LIMIT must be a non-negative integer.")
        try: limit_value=int(current_value.this)
        except (TypeError,ValueError):
            raise ValueError("LIMIT must be a non-negative integer.")
        if limit_value<0: raise ValueError("Negative LIMIT values are not allowed.")
    else:
        limit_value=None
    if limit_value is None or limit_value>MAX_QUERY_ROWS:
        query=query.limit(MAX_QUERY_ROWS, copy=False)
    return query.sql(dialect=dialect)

def run_sql(conn, dbt, sql, allowed_tables=None):
    if allowed_tables is None: allowed_tables=get_schema(conn, dbt).keys()
    safe_sql=validate_read_query(sql, dbt, allowed_tables)
    cur=conn.cursor()
    if dbt == "sqlite":
        readonly_actions={sqlite3.SQLITE_SELECT,sqlite3.SQLITE_READ,sqlite3.SQLITE_FUNCTION,sqlite3.SQLITE_RECURSIVE}
        allowed={str(name).casefold() for name in allowed_tables}
        def authorize(action,arg1,arg2,dbname,source):
            if action not in readonly_actions: return sqlite3.SQLITE_DENY
            if action == sqlite3.SQLITE_READ and arg1 and arg1.casefold() not in allowed:
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        conn.set_authorizer(authorize)
        deadline=time.monotonic()+QUERY_TIMEOUT_SECONDS
        conn.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
    cur.execute(safe_sql)
    if dbt in ("sqlite","postgresql"):
        cols=[d[0] for d in (cur.description or [])]
        rows=[dict(zip(cols,r)) for r in cur.fetchmany(MAX_QUERY_ROWS)]
    else:
        rows=cur.fetchmany(MAX_QUERY_ROWS) or []; cols=list(rows[0].keys()) if rows else []
    return rows, cols

def extract_sql(text):
    for pat in [r"```sql\s*(.*?)```",r"```\s*(SELECT.*?)```",r"(SELECT\b.*?;)",r"(SELECT\b.+)"]:
        m=re.search(pat,text,re.DOTALL|re.IGNORECASE)
        if m:
            s=m.group(1).strip()
            return s if s.endswith(";") else s+";"
    return None

# ── Demo DB ────────────────────────────────────────────────────────────────────
def make_demo():
    if os.path.exists(DEMO): return
    print("Creating demo database…")
    import random; random.seed(42)
    conn=sqlite3.connect(DEMO); c=conn.cursor()
    c.executescript("""
    CREATE TABLE customers(id INTEGER PRIMARY KEY,name TEXT,email TEXT,city TEXT,segment TEXT,join_date TEXT);
    CREATE TABLE products(id INTEGER PRIMARY KEY,name TEXT,category TEXT,price REAL,cost REAL,stock INTEGER);
    CREATE TABLE orders(id INTEGER PRIMARY KEY,customer_id INTEGER,order_date TEXT,status TEXT,total_amount REAL,discount_pct REAL);
    CREATE TABLE order_items(id INTEGER PRIMARY KEY,order_id INTEGER,product_id INTEGER,quantity INTEGER,unit_price REAL);
    CREATE TABLE marketing_campaigns(id INTEGER PRIMARY KEY,name TEXT,channel TEXT,budget REAL,spent REAL,leads INTEGER,conversions INTEGER,start_date TEXT,end_date TEXT);
    """)
    cities=["Mumbai","Delhi","Bangalore","Hyderabad","Chennai","Pune","Ahmedabad","Kolkata","Jaipur","Surat"]
    segs=["Enterprise","SMB","Startup","Individual"]
    custs=[(i,f"Company {i}",f"user{i}@co.com",random.choice(cities),random.choice(segs),
            (datetime(2023,1,1)+timedelta(days=random.randint(0,700))).strftime("%Y-%m-%d")) for i in range(1,101)]
    c.executemany("INSERT INTO customers VALUES(?,?,?,?,?,?)",custs)
    cats={"Electronics":["Laptop Pro","Smartphone X","Tablet Air","4K Monitor","Keyboard Elite","Wireless Mouse"],
          "Software":["CRM Suite","Analytics Pro","Cloud Storage","Security Shield","HR Platform"],
          "Services":["Consulting","Training","Support","Implementation","Audit"]}
    prods=[]; pid=1
    for cat,items in cats.items():
        for item in items:
            p=round(random.uniform(500,80000),2)
            prods.append((pid,item,cat,p,round(p*.55,2),random.randint(5,300))); pid+=1
    total_p=pid-1
    c.executemany("INSERT INTO products VALUES(?,?,?,?,?,?)",prods)
    stats=["completed","completed","completed","pending","cancelled"]
    ords=[(i,random.randint(1,100),(datetime(2023,6,1)+timedelta(days=random.randint(0,550))).strftime("%Y-%m-%d"),
           random.choice(stats),round(random.uniform(1000,150000),2),round(random.uniform(0,.25),2)) for i in range(1,601)]
    c.executemany("INSERT INTO orders VALUES(?,?,?,?,?,?)",ords)
    items=[]; iid=1
    for oid in range(1,601):
        for _ in range(random.randint(1,5)):
            p=random.randint(1,total_p); qty=random.randint(1,10); price=prods[p-1][3]
            items.append((iid,oid,p,qty,price)); iid+=1
    c.executemany("INSERT INTO order_items VALUES(?,?,?,?,?)",items)
    chs=["Google Ads","LinkedIn","Email","Facebook","Events","SEO","Referral"]
    camps=[]
    for i in range(1,26):
        b=round(random.uniform(10000,800000),2); sp=round(b*random.uniform(.4,1.0),2)
        l=random.randint(50,3000); cv=random.randint(5,int(l*.35)+1)
        s=(datetime(2023,1,1)+timedelta(days=random.randint(0,500))).strftime("%Y-%m-%d")
        e=(datetime.strptime(s,"%Y-%m-%d")+timedelta(days=random.randint(30,90))).strftime("%Y-%m-%d")
        camps.append((i,f"Campaign {i}",random.choice(chs),b,sp,l,cv,s,e))
    c.executemany("INSERT INTO marketing_campaigns VALUES(?,?,?,?,?,?,?,?,?)",camps)
    conn.commit(); conn.close(); print("✅ Demo DB ready")

make_demo()

# ── API Routes ─────────────────────────────────────────────────────────────────
@app.route("/api/health")
def health():
    return jsonify({"ok":True,"groq":bool(GROQ_KEY),"gemini":bool(GEMINI_KEY),
                    "sql_parser":bool(sqlglot),"v":"5.0"})

@app.errorhandler(413)
def request_too_large(_error):
    return jsonify({"error":"Request exceeds the 10 MiB limit."}),413

@app.route("/api/connect",methods=["POST"])
def connect():
    cfg=(request.json or {}).get("config",{})
    conn=None
    try:
        conn,dbt=get_conn(cfg); schema=get_schema(conn,dbt)
        db_ref=session.get("db_ref") or hashlib.sha256(os.urandom(32)).hexdigest()
        DB_CONFIGS[db_ref]=cfg
        session["db_ref"]=db_ref
        return jsonify({"ok":True,"schema":schema,"tables":len(schema),
                        "total_rows":sum(t["row_count"] for t in schema.values()),"db_type":dbt})
    except Exception:
        return jsonify({"ok":False,"error":"Could not connect or inspect the selected database."}),400
    finally:
        if conn: conn.close()

@app.route("/api/schema")
def schema_route():
    cfg=session_db_config()
    conn=None
    try:
        conn,dbt=get_conn(cfg); schema=get_schema(conn,dbt)
        return jsonify({"schema":schema,"db_type":dbt})
    except Exception:
        return jsonify({"error":"Could not inspect the selected database."}),400
    finally:
        if conn: conn.close()

@app.route("/api/query",methods=["POST"])
def query():
    q=(request.json or {}).get("question","").strip()
    if not q: return jsonify({"error":"No question"}),400
    if sqlglot is None:
        return jsonify({"error":"SQL safety parser is unavailable. Install project requirements."}),503
    cfg=session_db_config()
    conn=None
    try:
        conn,dbt=get_conn(cfg); schema=get_schema(conn,dbt)
        schema_txt="\n".join(f"Table `{t}` ({i['row_count']} rows): "+", ".join(f"{c['name']} {c['type']}" for c in i["columns"])
                             for t,i in schema.items())
        sql_resp=ai([
            {"role":"system","content":f"You are an expert SQL analyst.\nDB: {dbt}\nSchema:\n{schema_txt}\nOutput ONLY SQL inside ```sql``` fences. SELECT only. LIMIT 500."},
            {"role":"user","content":q}
        ])
        sql=extract_sql(sql_resp)
        if not sql: return jsonify({"error":"The AI response did not contain a usable SQL query."}),400
        rows,cols=run_sql(conn,dbt,sql,allowed_tables=schema.keys())
        conn.close(); conn=None
        insight=ai([
            {"role":"system","content":"Senior business analyst. Give 4-5 specific bullet point insights with numbers. Under 150 words. Markdown bullets."},
            {"role":"user","content":f"Q: {q}\nSQL: {sql}\nData (first 10): {json.dumps(rows[:10],default=str)}\nTotal: {len(rows)}"}
        ])
        chart="bar"
        if cols and rows:
            fc=cols[0].lower()
            if any(w in fc for w in ["date","month","year","week","day"]): chart="line"
            elif len(rows)<=6: chart="pie"
        return jsonify({"ok":True,"sql":sql,"rows":rows,"columns":cols,"row_count":len(rows),"insight":insight,"chart_type":chart})
    except ValueError as e:
        return jsonify({"error":str(e)}),400
    except SQLSafetyDependencyError:
        return jsonify({"error":"SQL safety parser is unavailable. Install project requirements."}),503
    except Exception:
        traceback.print_exc()
        return jsonify({"error":"Analysis failed. Check the query, database, and AI provider availability."}),500
    finally:
        if conn: conn.close()

@app.route("/api/sql",methods=["POST"])
def sql_run():
    sql=(request.json or {}).get("sql","").strip()
    if not sql: return jsonify({"error":"No SQL"}),400
    cfg=session_db_config()
    conn=None
    try:
        conn,dbt=get_conn(cfg); schema=get_schema(conn,dbt)
        rows,cols=run_sql(conn,dbt,sql,allowed_tables=schema.keys())
        return jsonify({"ok":True,"rows":rows,"columns":cols,"row_count":len(rows)})
    except ValueError as e:
        return jsonify({"error":str(e)}),400
    except SQLSafetyDependencyError:
        return jsonify({"error":"SQL safety parser is unavailable. Install project requirements."}),503
    except Exception:
        traceback.print_exc()
        return jsonify({"error":"Query failed. Check SQL syntax and database availability."}),500
    finally:
        if conn: conn.close()

@app.route("/api/suggest")
def suggest():
    cfg=session_db_config()
    try:
        conn,dbt=get_conn(cfg); schema=get_schema(conn,dbt); conn.close()
        tables=", ".join(schema.keys())
        resp=ai([
            {"role":"system","content":"Return ONLY a JSON array of 6 strings. No markdown, no preamble, just the array."},
            {"role":"user","content":f"Tables: {tables}. Generate 6 business questions a CEO would ask."}
        ])
        clean=re.sub(r"```json|```","",resp).strip()
        return jsonify({"suggestions":json.loads(clean)[:6]})
    except:
        return jsonify({"suggestions":["Top 10 customers by revenue?","Monthly sales trend?","Best product by margin?","Customer city breakdown?","Campaign ROI by channel?","Order status summary?"]})

@app.route("/api/upload-csv",methods=["POST"])
def upload_csv():
    upload=request.files.get("file")
    if not upload: return jsonify({"error":"No file"}),400
    filename=os.path.basename(upload.filename or "")
    if not filename.lower().endswith(".csv"):
        return jsonify({"error":"Upload a .csv file."}),400
    try:
        raw=upload.stream.read(app.config["MAX_CONTENT_LENGTH"]+1)
        if len(raw)>app.config["MAX_CONTENT_LENGTH"]:
            return jsonify({"error":"CSV exceeds the 10 MiB upload limit."}),413
        content=raw.decode("utf-8-sig")
        reader=csv.reader(io.StringIO(content,newline=""),strict=True)
        raw_headers=next(reader,None)
        if not raw_headers or len(raw_headers)>200:
            return jsonify({"error":"CSV needs between 1 and 200 columns."}),400
        columns=[]
        used=set()
        for idx,header in enumerate(raw_headers,1):
            col=re.sub(r"[^\w]+","_",(header or "").strip()).strip("_") or f"column_{idx}"
            if col[0].isdigit(): col=f"col_{col}"
            base=col; suffix=2
            while col.casefold() in used:
                col=f"{base}_{suffix}"; suffix+=1
            used.add(col.casefold()); columns.append(col)
        rows=[]
        for row in reader:
            if not row or all(not value.strip() for value in row): continue
            if len(row)!=len(columns):
                return jsonify({"error":"CSV rows must have the same number of fields as the header."}),400
            rows.append(row)
            if len(rows)>50_000 or len(rows)*len(columns)>1_000_000:
                return jsonify({"error":"CSV exceeds the 50,000 row or 1,000,000 cell limit."}),413
        if not rows: return jsonify({"error":"CSV contains no data rows."}),400
    except (UnicodeDecodeError,csv.Error,StopIteration):
        return jsonify({"error":"CSV must be valid UTF-8 with a valid header and rows."}),400

    def infer(values):
        populated=[value.strip() for value in values if value.strip()]
        if not populated: return "TEXT"
        try:
            for value in populated: int(value)
            return "INTEGER"
        except ValueError: pass
        try:
            for value in populated: float(value)
            return "REAL"
        except ValueError: return "TEXT"
    types=[infer([row[i] for row in rows]) for i in range(len(columns))]
    stem=os.path.splitext(filename)[0].lower()
    name=re.sub(r"[^\w]+","_",stem).strip("_") or "uploaded_data"
    if name[0].isdigit(): name=f"table_{name}"
    sid=session.get("sid") or hashlib.sha256(os.urandom(32)).hexdigest()
    session["sid"]=sid
    dbp=os.path.join(UPL,f"{sid}.db")
    quoted_table='"'+name.replace('"','""')+'"'
    quoted_columns=", ".join('"'+c.replace('"','""')+'" '+t for c,t in zip(columns,types))
    conn=sqlite3.connect(dbp)
    try:
        cur=conn.cursor()
        cur.execute(f"DROP TABLE IF EXISTS {quoted_table}")
        cur.execute(f"CREATE TABLE {quoted_table} ({quoted_columns})")
        placeholders=", ".join("?" for _ in columns)
        cur.executemany(f"INSERT INTO {quoted_table} VALUES ({placeholders})",rows)
        conn.commit()
    finally:
        conn.close()
    db_ref=session.get("db_ref") or hashlib.sha256(os.urandom(32)).hexdigest()
    DB_CONFIGS[db_ref]={"type":"sqlite","path":dbp}
    session["db_ref"]=db_ref
    return jsonify({"ok":True,"table":name,"rows":len(rows),"columns":columns,"file":filename})

@app.route("/api/insights/auto",methods=["POST"])
def auto_insights():
    table=(request.json or {}).get("table","")
    cfg=session_db_config()
    if not table: return jsonify({"error":"No table"}),400
    conn=None
    try:
        conn,dbt=get_conn(cfg); schema=get_schema(conn,dbt)
        if table not in schema: return jsonify({"error":"Table is not available."}),400
        rows,cols=run_sql(conn,dbt,f"SELECT * FROM `{table}` LIMIT 100",allowed_tables=schema.keys())
        conn.close(); conn=None
        insight=ai([
            {"role":"system","content":"Senior data analyst. Give 5-7 specific, actionable insights with numbers. Markdown bullets."},
            {"role":"user","content":f"Table: {table}\nColumns: {cols}\nData:\n{json.dumps(rows[:50],default=str)}"}
        ])
        return jsonify({"ok":True,"insight":insight,"table":table})
    except Exception:
        traceback.print_exc()
        return jsonify({"error":"Could not generate insights for this table."}),500
    finally:
        if conn: conn.close()

if __name__=="__main__":
    print(f"\n{'='*50}\n  🧠  DataWise AI v5.0\n{'='*50}")
    print(f"  Groq  : {'✅' if GROQ_KEY else '❌ Add GROQ_API_KEY to .env'}")
    print(f"  Gemini: {'✅' if GEMINI_KEY else '⚠️  optional'}")
    print(f"  Open  : http://localhost:5000\n{'='*50}\n")
    app.run(debug=False, port=5000, host=HOST)
