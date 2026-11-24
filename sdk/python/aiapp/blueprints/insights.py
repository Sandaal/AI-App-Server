"""Insights: questions about data, answered by querying it.

Route ``POST /ask`` ``{"question": "..."}`` → ``{"answer", "queries": [{database,
sql, columns, rows, truncated}], "error"?}``.

Manifest::

    insights:
      databases:
        - { name: sales, driver: postgres, dsn: "${SALES_DB}", tables: [orders, customers], max_rows: 200 }
      files: [./data/]          # CSV files, queried as SQLite tables named after the files
      instructions: "Revenue is orders.total; fiscal years start in April."

The model sees the tables and their columns, writes SQL through a
``run_sql`` tool, reads the rows and answers. Database queries run in the
core (read-only checks, row and time limits, PostgreSQL read-only
transactions); CSV files are loaded into an in-memory SQLite database in
the worker, opened read-only. Use database logins that can only read.
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import sqlite3

from aiapp import ModelError, Request, Response, SQLError, app

FILES = "files"
MAX_STEPS = 6
SHOW_ROWS = 50

SYSTEM = (
    "You answer questions about the user's data by querying it with SQL. Look at the tables and columns, call "
    "run_sql with one SELECT query at a time, read the rows, and answer in plain language with the key numbers. "
    "If a query fails, fix it and try again. Never invent numbers: every figure must come from a query result. "
    "Use the SQL dialect of the database you query (SQLite for 'files'). Text values go in single quotes "
    "('North'); double quotes are only for column names."
)


def _calls_in_text(text: str) -> list[dict]:
    """Small local models sometimes write the tool call as JSON text instead of
    calling it; accept {"name": "run_sql", "parameters"|"arguments": {...}}."""
    calls = []
    for m in re.finditer(r'\{\s*"name"\s*:\s*"run_sql"', text):
        depth, end = 0, None
        for i in range(m.start(), len(text)):
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            if depth == 0:
                end = i + 1
                break
        try:
            obj = json.loads(text[m.start():end]) if end else None
        except json.JSONDecodeError:
            obj = None
        args = (obj or {}).get("parameters") or (obj or {}).get("arguments")
        if isinstance(args, dict) and args.get("query"):
            calls.append({"id": f"text-{len(calls)}", "name": "run_sql", "arguments": args})
    return calls

_csv_db: sqlite3.Connection | None = None
_csv_tables: list[dict] = []


def _json(obj, status=200) -> Response:
    return Response(json.dumps(obj, default=str), status=status, content_type="application/json")


def _config() -> dict:
    return app.manifest.get("insights") or {}


def _number(v: str):
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v


def _load_csv() -> None:
    """Load the configured CSV files into an in-memory SQLite database (once)."""
    global _csv_db, _csv_tables
    if _csv_db is not None:
        return
    db = sqlite3.connect(":memory:", check_same_thread=False)
    tables = []
    paths = []
    for entry in _config().get("files") or []:
        p = os.path.join(os.getcwd(), entry)
        if os.path.isdir(p):
            paths += [os.path.join(p, f) for f in sorted(os.listdir(p)) if f.lower().endswith(".csv")]
        elif p.lower().endswith(".csv"):
            paths.append(p)
    for path in paths:
        name = re.sub(r"\W+", "_", os.path.splitext(os.path.basename(path))[0]).strip("_").lower() or "data"
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))
        if not rows:
            continue
        cols = [re.sub(r"\W+", "_", c).strip("_").lower() or f"col{i}" for i, c in enumerate(rows[0])]
        db.execute(f'CREATE TABLE "{name}" ({", ".join(chr(34) + c + chr(34) for c in cols)})')
        db.executemany(f'INSERT INTO "{name}" VALUES ({", ".join("?" for _ in cols)})',
                       [[_number(v) for v in (r + [""] * len(cols))[:len(cols)]] for r in rows[1:200_001]])
        tables.append({"name": name, "columns": cols, "rows": len(rows) - 1})
    db.commit()
    db.execute("PRAGMA query_only = ON")  # the model can only read
    _csv_db, _csv_tables = db, tables


def _query_files(sql: str) -> dict:
    q = sql.strip().rstrip(";")
    if ";" in re.sub(r"'(?:[^']|'')*'", "", q) or not re.match(r"(?is)^\s*(select|with)\b", q):
        raise SQLError("one SELECT query at a time")
    cur = _csv_db.execute(q)
    cols = [d[0] for d in cur.description or []]
    rows = cur.fetchmany(201)
    return {"columns": cols, "rows": [[str(v) for v in r] for r in rows[:200]], "truncated": len(rows) > 200}


async def _schema() -> str:
    lines = []
    for d in _config().get("databases") or []:
        try:
            tables = await app.sql.tables(d["name"])
        except Exception as e:  # unreachable database: say so, keep the others
            lines.append(f"Database {d['name']} ({d['driver']}): unavailable ({e})")
            continue
        lines.append(f"Database {d['name']} ({d['driver']}):")
        lines += [f"  {t['name']}({', '.join(t['columns'])})" for t in tables]
    if _config().get("files"):
        _load_csv()
        lines.append("Database files (SQLite, from CSV files):")
        lines += [f"  {t['name']}({', '.join(t['columns'])})  -- {t['rows']} rows" for t in _csv_tables]
    return "\n".join(lines)


RUN_SQL = {
    "name": "run_sql",
    "description": "Run one read-only SELECT query and get the rows back.",
    "parameters": {
        "type": "object",
        "properties": {
            "database": {"type": "string", "description": "Which database: one of the names listed"},
            "query": {"type": "string", "description": "A single SELECT statement"},
        },
        "required": ["database", "query"],
    },
}


async def ask(req: Request):
    try:
        body = req.json() if req.body.lstrip().startswith(b"{") else {"question": req.text}
    except json.JSONDecodeError:
        return _json({"error": "invalid JSON"}, 400)
    question = str(body.get("question") or "").strip()
    if not question:
        return _json({"error": 'send {"question": "..."}'}, 400)
    cfg = _config()
    system = SYSTEM + "\n\nTables:\n" + await _schema()
    if cfg.get("instructions"):
        system += "\n\nNotes about the data:\n" + str(cfg["instructions"])
    convo = [{"role": "user", "content": question}]
    queries = []
    try:
        for _ in range(int(cfg.get("max_steps") or MAX_STEPS)):
            reply = await app.models.chat.turn(convo, tools=[RUN_SQL], system=system, temperature=0)
            if not reply["calls"]:
                reply["calls"] = _calls_in_text(reply["text"])
                if reply["calls"]:
                    reply["text"] = ""
            if not reply["calls"]:
                return _json({"answer": reply["text"], "queries": queries})
            convo.append({"role": "assistant", "content": reply["text"], "tool_calls": reply["calls"]})
            for call in reply["calls"]:
                db, sql = str(call["arguments"].get("database", "")), str(call["arguments"].get("query", ""))
                entry = {"database": db, "sql": sql}
                try:
                    res = _query_files(sql) if db == FILES and cfg.get("files") else await app.sql.query(db, sql)
                    entry.update(columns=res["columns"], rows=res["rows"][:SHOW_ROWS], truncated=res["truncated"] or len(res["rows"]) > SHOW_ROWS)
                    out = {"columns": res["columns"], "rows": res["rows"], "truncated": res["truncated"]}
                    content = json.dumps(out)[:12_000]
                except (SQLError, sqlite3.Error) as e:
                    entry["error"] = str(e)
                    content = f"Error: {e}"
                queries.append(entry)
                convo.append({"role": "tool", "tool_call_id": call["id"], "content": content})
    except ModelError as e:
        return _json({"error": str(e), "code": e.code, "queries": queries}, 429 if e.code == "budget_exceeded" else 502)
    return _json({"answer": None, "error": "stopped before reaching an answer", "queries": queries})
