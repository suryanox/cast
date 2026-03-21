from __future__ import annotations
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import Run, Step, ToolCall, RunStatus, StepType

CAST_DIR = Path.home() / ".cast"
DB_PATH = CAST_DIR / "runs.db"


def _connect() -> sqlite3.Connection:
    CAST_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY,
            name TEXT,
            status TEXT,
            started_at TEXT,
            ended_at TEXT,
            error TEXT,
            forked_from TEXT,
            forked_at_step INTEGER
        );

        CREATE TABLE IF NOT EXISTS steps (
            id TEXT PRIMARY KEY,
            run_id TEXT,
            index_ INTEGER,
            type TEXT,
            model TEXT,
            prompt TEXT,
            response TEXT,
            tool_calls TEXT,
            input_tokens INTEGER,
            output_tokens INTEGER,
            latency_ms INTEGER,
            timestamp TEXT,
            FOREIGN KEY(run_id) REFERENCES runs(id)
        );
    """)
    conn.commit()


def save_run(run: Run):
    conn = _connect()
    conn.execute("""
        INSERT OR REPLACE INTO runs
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run.id, run.name, run.status.value,
        run.started_at.isoformat(),
        run.ended_at.isoformat() if run.ended_at else None,
        run.error, run.forked_from, run.forked_at_step
    ))
    for step in run.steps:
        conn.execute("""
            INSERT OR REPLACE INTO steps
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            step.id, step.run_id, step.index, step.type.value,
            step.model,
            json.dumps(_serialize_messages(step.prompt)),
            step.response,
            json.dumps([vars(tc) for tc in step.tool_calls]),
            step.input_tokens, step.output_tokens,
            step.latency_ms,
            step.timestamp.isoformat()
        ))
    conn.commit()
    conn.close()


def load_run(run_id: str) -> Optional[Run]:
    conn = _connect()
    row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    if not row:
        return None
    steps = _load_steps(conn, run_id)
    conn.close()
    return _row_to_run(row, steps)


def list_runs(limit: int = 20) -> list[Run]:
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,)
    ).fetchall()
    runs = []
    for row in rows:
        steps = _load_steps(conn, row["id"])
        runs.append(_row_to_run(row, steps))
    conn.close()
    return runs


def _load_steps(conn: sqlite3.Connection, run_id: str) -> list[Step]:
    rows = conn.execute(
        "SELECT * FROM steps WHERE run_id = ? ORDER BY index_", (run_id,)
    ).fetchall()
    steps = []
    for row in rows:
        tool_calls = [
            ToolCall(**tc) for tc in json.loads(row["tool_calls"])
        ]
        steps.append(Step(
            id=row["id"],
            run_id=row["run_id"],
            index=row["index_"],
            type=StepType(row["type"]),
            model=row["model"],
            prompt=json.loads(row["prompt"]),
            response=row["response"],
            tool_calls=tool_calls,
            input_tokens=row["input_tokens"],
            output_tokens=row["output_tokens"],
            latency_ms=row["latency_ms"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
        ))
    return steps


def _row_to_run(row: sqlite3.Row, steps: list[Step]) -> Run:
    return Run(
        id=row["id"],
        name=row["name"],
        status=RunStatus(row["status"]),
        steps=steps,
        started_at=datetime.fromisoformat(row["started_at"]),
        ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
        error=row["error"],
        forked_from=row["forked_from"],
        forked_at_step=row["forked_at_step"],
    )

def clear_runs() -> int:
    conn = _connect()
    count = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    conn.execute("DELETE FROM steps")
    conn.execute("DELETE FROM runs")
    conn.commit()
    conn.close()
    return count

def _serialize_messages(messages: list) -> list:
    result = []
    for m in messages:
        if isinstance(m, dict):
            result.append(m)
        else:
            d = {"role": getattr(m, "role", "unknown")}
            content = getattr(m, "content", None)
            if content:
                d["content"] = content
            tool_calls = getattr(m, "tool_calls", None)
            if tool_calls:
                d["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    }
                    for tc in tool_calls
                ]
            result.append(d)
    return result