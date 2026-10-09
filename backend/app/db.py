"""Tiny SQLite snapshot store; the assessment calculation itself remains stateless."""
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path


def _database_path() -> Path:
    url = os.getenv("DATABASE_URL", "sqlite:///./phenocredit.db")
    prefix = "sqlite:///"
    raw = url[len(prefix):] if url.startswith(prefix) else "./phenocredit.db"
    path = Path(raw)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[1] / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def _connect():
    con = sqlite3.connect(_database_path())
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("""CREATE TABLE IF NOT EXISTS borrowers (
        borrower_id TEXT PRIMARY KEY, record_json TEXT NOT NULL, synthetic INTEGER NOT NULL
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS loans (
        loan_id TEXT PRIMARY KEY, borrower_id TEXT NOT NULL, record_json TEXT NOT NULL,
        FOREIGN KEY(borrower_id) REFERENCES borrowers(borrower_id)
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS data_sources (
        source_id TEXT PRIMARY KEY, record_json TEXT NOT NULL
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS scenario_snapshots (
        scenario_id TEXT PRIMARY KEY,
        borrower_id TEXT NOT NULL,
        input_hash TEXT NOT NULL,
        request_json TEXT NOT NULL,
        result_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        role TEXT NOT NULL,
        name TEXT NOT NULL,
        email TEXT UNIQUE,
        phone TEXT UNIQUE,
        password_hash TEXT,
        linked_borrower_id TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS otp_sessions (
        id TEXT PRIMARY KEY,
        phone TEXT NOT NULL,
        otp_hash TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        used INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    )""")
    try:
        with con:
            yield con
    finally:
        con.close()


def seed_demo_records(borrowers: dict, sources: list[dict]) -> None:
    """Idempotently seed the local, synthetic demo borrower and provenance records."""
    with _connect() as con:
        for borrower_id, row in borrowers.items():
            borrower_record = {k: str(v) if isinstance(v, Decimal) else v.isoformat() if hasattr(v, "isoformat") else v
                               for k, v in row.items()}
            loan_record = {
                "loan_id": f"L-{borrower_id}", "borrower_id": borrower_id,
                "principal_inr": str(row["loan_principal_inr"]), "annual_rate": str(row["annual_rate"]),
                "disbursed_at": row["disbursed_at"].isoformat(), "due_at": row["due_at"].isoformat(),
                "synthetic": True,
                "events": [
                    {"date": row["disbursed_at"].isoformat(), "kind": "disbursement", "amount_inr": str(row["loan_principal_inr"]), "source_status": "synthetic"},
                    {"date": (row["sowing_date"] + timedelta(days=8)).isoformat(), "kind": "crop_inputs", "amount_inr": str(-row["input_cost_inr"]), "source_status": "assumed"},
                    {"date": row["due_at"].isoformat(), "kind": "bank_due", "amount_inr": "pending_scenario_calculation", "source_status": "simulated"},
                    {"date": row["harvest_date"].isoformat(), "kind": "expected_crop_sale", "amount_inr": "pending_scenario_calculation", "source_status": "assumed"},
                ],
            }
            con.execute("INSERT INTO borrowers VALUES (?, ?, 1) ON CONFLICT(borrower_id) DO UPDATE SET record_json=excluded.record_json",
                        (borrower_id, json.dumps(borrower_record, sort_keys=True)))
            con.execute("INSERT INTO loans VALUES (?, ?, ?) ON CONFLICT(loan_id) DO UPDATE SET record_json=excluded.record_json",
                        (loan_record["loan_id"], borrower_id, json.dumps(loan_record, sort_keys=True)))
        for source in sources:
            con.execute("INSERT INTO data_sources VALUES (?, ?) ON CONFLICT(source_id) DO UPDATE SET record_json=excluded.record_json",
                        (source["id"], json.dumps(source, sort_keys=True)))


def list_borrower_records() -> list[dict]:
    with _connect() as con:
        return [json.loads(row[0]) for row in con.execute("SELECT record_json FROM borrowers ORDER BY borrower_id")]


def get_borrower_record(borrower_id: str) -> dict | None:
    with _connect() as con:
        row = con.execute("SELECT record_json FROM borrowers WHERE borrower_id=?", (borrower_id,)).fetchone()
    return json.loads(row[0]) if row else None


def get_loan_record(borrower_id: str) -> dict | None:
    with _connect() as con:
        row = con.execute("SELECT record_json FROM loans WHERE borrower_id=?", (borrower_id,)).fetchone()
    return json.loads(row[0]) if row else None


def list_source_records() -> list[dict]:
    with _connect() as con:
        return [json.loads(row[0]) for row in con.execute("SELECT record_json FROM data_sources ORDER BY source_id")]


def save_scenario(scenario_id: str, borrower_id: str, input_hash: str, request: dict, result: dict) -> None:
    with _connect() as con:
        con.execute("""INSERT INTO scenario_snapshots
            (scenario_id, borrower_id, input_hash, request_json, result_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(scenario_id) DO NOTHING""",
            (scenario_id, borrower_id, input_hash, json.dumps(request, sort_keys=True),
             json.dumps(result, sort_keys=True), datetime.now(timezone.utc).isoformat()))


def get_scenario(scenario_id: str) -> dict | None:
    with _connect() as con:
        row = con.execute("SELECT result_json, request_json FROM scenario_snapshots WHERE scenario_id=?", (scenario_id,)).fetchone()
    if not row:
        return None
    result = json.loads(row["result_json"])
    # Earlier snapshots predate the request echo used by the reopen UI. Keep
    # immutable results intact and fill that UI-only field from the stored request.
    from app.schemas import ScenarioRequest
    stored_request = result.get("scenario_request") or json.loads(row["request_json"])
    result["scenario_request"] = ScenarioRequest.model_validate(stored_request).model_dump(mode="json")
    return result


def list_scenarios(limit: int = 50) -> list[dict]:
    """List immutable saved assessments for report and snapshot reopening."""
    with _connect() as con:
        rows = con.execute(
            "SELECT scenario_id, borrower_id, input_hash, created_at, result_json "
            "FROM scenario_snapshots ORDER BY created_at DESC, scenario_id DESC LIMIT ?",
            (max(1, min(limit, 100)),),
        ).fetchall()
    summaries = []
    for row in rows:
        result = json.loads(row["result_json"])
        summaries.append({"scenario_id": row["scenario_id"], "borrower_id": row["borrower_id"],
                          "input_hash": row["input_hash"], "created_at": row["created_at"],
                          "engine_version": result["engine_version"],
                          "comparison_context_hash": result["comparison_context_hash"],
                          "cash_gap_inr": result["stress"]["cash_gap_inr"],
                          "action_status": result["action_status"]})
    return summaries
