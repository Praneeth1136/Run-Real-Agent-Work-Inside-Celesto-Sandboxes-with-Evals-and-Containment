import os
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ledger:ledger@localhost:5432/ledger")

# Fallback store if running standalone outside docker without postgres
_MEMORY_RUNS: List[Dict[str, Any]] = [
    {
        "run_id": "run-seed-001",
        "sandbox_name": "sbx-seeddemo1",
        "problem_id": "problem-seed-demo",
        "state": "deleted",
        "execution_target": "celesto_sandbox",
        "created_at": "2026-11-06T12:00:00Z"
    }
]

def get_db_connection():
    if not DATABASE_URL or DATABASE_URL.startswith("memory://"):
        return None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        return None

def init_db():
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS runs (
                        run_id VARCHAR(128) PRIMARY KEY,
                        sandbox_name VARCHAR(128) NOT NULL,
                        problem_id VARCHAR(128) NOT NULL,
                        state VARCHAR(32) NOT NULL,
                        execution_target VARCHAR(64) NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cur.execute("""
                    INSERT INTO runs (run_id, sandbox_name, problem_id, state, execution_target)
                    VALUES ('run-seed-001', 'sbx-seeddemo1', 'problem-seed-demo', 'deleted', 'celesto_sandbox')
                    ON CONFLICT (run_id) DO NOTHING;
                """)
            conn.commit()
        finally:
            conn.close()

def list_runs() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT run_id, sandbox_name, problem_id, state, execution_target, created_at FROM runs ORDER BY created_at ASC;")
                rows = cur.fetchall()
                result = []
                for r in rows:
                    row_dict = dict(r)
                    if row_dict.get("created_at"):
                        row_dict["created_at"] = row_dict["created_at"].isoformat()
                    result.append(row_dict)
                return result
        finally:
            conn.close()
    return _MEMORY_RUNS

def insert_run(run: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO runs (run_id, sandbox_name, problem_id, state, execution_target)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (run_id) DO UPDATE SET
                        sandbox_name = EXCLUDED.sandbox_name,
                        problem_id = EXCLUDED.problem_id,
                        state = EXCLUDED.state,
                        execution_target = EXCLUDED.execution_target
                    RETURNING run_id, sandbox_name, problem_id, state, execution_target, created_at;
                """, (run["run_id"], run["sandbox_name"], run["problem_id"], run["state"], run["execution_target"]))
                row = cur.fetchone()
            conn.commit()
            res = dict(row)
            if res.get("created_at"):
                res["created_at"] = res["created_at"].isoformat()
            return res
        finally:
            conn.close()
    
    # In-memory fallback
    existing = [r for r in _MEMORY_RUNS if r["run_id"] == run["run_id"]]
    if existing:
        existing[0].update(run)
        return existing[0]
    new_run = dict(run)
    new_run["created_at"] = "2026-11-06T15:00:00Z"
    _MEMORY_RUNS.append(new_run)
    return new_run

