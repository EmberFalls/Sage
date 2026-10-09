"""Tiny SQLite snapshot store; the assessment calculation itself remains stateless."""
import json
import hashlib
import os
import sqlite3
from uuid import uuid4
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path


def _database_path() -> Path:
    url = os.getenv("DATABASE_URL", "sqlite:///./sage.db")
    prefix = "sqlite:///"
    raw = url[len(prefix):] if url.startswith(prefix) else "./sage.db"
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
    con.execute("""CREATE TABLE IF NOT EXISTS warning_evidence (
        derivation_key TEXT PRIMARY KEY,
        assessment_id TEXT NOT NULL,
        rule TEXT NOT NULL,
        rule_version TEXT NOT NULL,
        evidence_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS intervention_proposals (
        proposal_id TEXT PRIMARY KEY,
        comparison_id TEXT NOT NULL,
        candidate_id TEXT NOT NULL,
        assessment_id TEXT NOT NULL,
        scenario_id TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        review_history_json TEXT NOT NULL,
        applied_simulation_json TEXT
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS warning_tasks (
        derivation_key TEXT PRIMARY KEY, status TEXT NOT NULL, assigned_to TEXT,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS warning_task_events (
        event_id TEXT PRIMARY KEY, derivation_key TEXT NOT NULL, operation TEXT NOT NULL,
        actor TEXT NOT NULL, reason TEXT NOT NULL, assigned_to TEXT, superseded_by TEXT,
        created_at TEXT NOT NULL, FOREIGN KEY(derivation_key) REFERENCES warning_tasks(derivation_key)
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS allocation_snapshots (
        allocation_id TEXT PRIMARY KEY, branch_id TEXT NOT NULL, input_json TEXT NOT NULL,
        result_json TEXT NOT NULL, created_at TEXT NOT NULL
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS comparison_bundles (
        bundle_id TEXT PRIMARY KEY, context_hash TEXT NOT NULL, bundle_json TEXT NOT NULL, created_at TEXT NOT NULL
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS scenario_supersessions (
        scenario_id TEXT PRIMARY KEY, supersedes_id TEXT NOT NULL, created_at TEXT NOT NULL
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS comparison_bundle_supersessions (
        bundle_id TEXT PRIMARY KEY, supersedes_bundle_id TEXT NOT NULL, created_at TEXT NOT NULL
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
        version INTEGER PRIMARY KEY,
        applied_at TEXT NOT NULL
    )""")
    con.execute("INSERT OR IGNORE INTO schema_migrations VALUES (1, ?)", (datetime.now(timezone.utc).isoformat(),))
    if con.execute("SELECT 1 FROM schema_migrations WHERE version=2").fetchone() is None:
        migration = Path(__file__).resolve().parents[1] / "migrations" / "0002_operations_and_source_snapshots.sql"
        con.executescript(migration.read_text(encoding="utf-8"))
        con.execute("INSERT INTO schema_migrations VALUES (2, ?)", (datetime.now(timezone.utc).isoformat(),))
    if con.execute("SELECT 1 FROM schema_migrations WHERE version=3").fetchone() is None:
        migration = Path(__file__).resolve().parents[1] / "migrations" / "0003_source_refresh_history.sql"
        con.executescript(migration.read_text(encoding="utf-8"))
        con.execute("INSERT INTO schema_migrations VALUES (3, ?)", (datetime.now(timezone.utc).isoformat(),))
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


def save_borrower_record(record: dict, *, create: bool = False) -> None:
    with _connect() as con:
        if create:
            con.execute("INSERT INTO borrowers VALUES (?, ?, ?)",
                        (record["id"], json.dumps(record, sort_keys=True), int(record.get("synthetic", True))))
        else:
            cursor = con.execute("UPDATE borrowers SET record_json=?, synthetic=? WHERE borrower_id=?",
                                 (json.dumps(record, sort_keys=True), int(record.get("synthetic", True)), record["id"]))
            if cursor.rowcount == 0:
                raise KeyError(record["id"])


def create_application(record: dict) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as con:
        con.execute("INSERT INTO applications VALUES (?, ?, ?, ?, ?, ?)",
                    (record["application_id"], record["borrower_id"], record["status"],
                     json.dumps(record, sort_keys=True), now, now))


def list_applications() -> list[dict]:
    with _connect() as con:
        rows = con.execute("SELECT record_json FROM applications ORDER BY created_at DESC, application_id DESC").fetchall()
    return [json.loads(row[0]) for row in rows]


def get_application(application_id: str) -> dict | None:
    with _connect() as con:
        row = con.execute("SELECT record_json FROM applications WHERE application_id=?", (application_id,)).fetchone()
    return json.loads(row[0]) if row else None


def update_application(record: dict) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as con:
        cursor = con.execute("UPDATE applications SET status=?, record_json=?, updated_at=? WHERE application_id=?",
                             (record["status"], json.dumps(record, sort_keys=True), now, record["application_id"]))
        if cursor.rowcount == 0:
            raise KeyError(record["application_id"])


def update_application_with_demo_loan(record: dict, borrower: dict, loan: dict) -> None:
    """Persist approval, requested principal, and the generated demo loan atomically."""
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as con:
        cursor = con.execute("UPDATE applications SET status=?, record_json=?, updated_at=? WHERE application_id=?",
                             (record["status"], json.dumps(record, sort_keys=True), now, record["application_id"]))
        if cursor.rowcount == 0:
            raise KeyError(record["application_id"])
        cursor = con.execute("UPDATE borrowers SET record_json=? WHERE borrower_id=?",
                             (json.dumps(borrower, sort_keys=True), borrower["id"]))
        if cursor.rowcount == 0:
            raise KeyError(borrower["id"])
        con.execute("INSERT INTO loans VALUES (?, ?, ?) ON CONFLICT(loan_id) DO UPDATE SET record_json=excluded.record_json",
                    (loan["loan_id"], borrower["id"], json.dumps(loan, sort_keys=True)))


def append_loan_event(loan_id: str, event: dict) -> dict | None:
    with _connect() as con:
        row = con.execute("SELECT borrower_id, record_json FROM loans WHERE loan_id=?", (loan_id,)).fetchone()
        if row is None:
            return None
        record = json.loads(row["record_json"])
        events = record.setdefault("posted_events", [])
        existing = next((item for item in events if item["event_id"] == event["event_id"]), None)
        if existing is not None:
            return record
        events.append(event)
        record["posted_events"] = sorted(events, key=lambda item: (item["date"], item["event_id"]))
        con.execute("UPDATE loans SET record_json=? WHERE loan_id=?", (json.dumps(record, sort_keys=True), loan_id))
        return record


def save_source_snapshot(snapshot_id: str, source_id: str, retrieved_at: str, content_sha256: str, record: dict) -> None:
    with _connect() as con:
        con.execute("INSERT INTO source_snapshots VALUES (?, ?, ?, ?, ?) ON CONFLICT(snapshot_id) DO NOTHING",
                    (snapshot_id, source_id, retrieved_at, content_sha256, json.dumps(record, sort_keys=True)))


def list_source_snapshots(source_id: str | None = None, *, include_content: bool = False) -> list[dict]:
    with _connect() as con:
        if source_id:
            rows = con.execute("SELECT record_json FROM source_snapshots WHERE source_id=? ORDER BY retrieved_at DESC",
                               (source_id,)).fetchall()
        else:
            rows = con.execute("SELECT record_json FROM source_snapshots ORDER BY retrieved_at DESC").fetchall()
    records = [json.loads(row[0]) for row in rows]
    if not include_content:
        for record in records:
            record.pop("raw_body_utf8", None)
            record.pop("payload", None)
    return records


def get_source_snapshot(snapshot_id: str) -> dict | None:
    with _connect() as con:
        row = con.execute("SELECT record_json FROM source_snapshots WHERE snapshot_id=?", (snapshot_id,)).fetchone()
    return json.loads(row[0]) if row else None


def save_source_refresh_event(record: dict) -> None:
    with _connect() as con:
        con.execute("INSERT INTO source_refresh_events VALUES (?, ?, ?, ?, ?, ?)",
                    (record["refresh_id"], record["source_id"], record["attempted_at"], record["status"],
                     record.get("snapshot_id"), record.get("error_code")))


def list_source_refresh_events(source_id: str | None = None, limit: int = 50) -> list[dict]:
    with _connect() as con:
        if source_id:
            rows = con.execute("SELECT * FROM source_refresh_events WHERE source_id=? ORDER BY attempted_at DESC LIMIT ?",
                               (source_id, limit)).fetchall()
        else:
            rows = con.execute("SELECT * FROM source_refresh_events ORDER BY attempted_at DESC LIMIT ?",
                               (limit,)).fetchall()
    return [dict(row) for row in rows]


def get_loan_record(borrower_id: str) -> dict | None:
    with _connect() as con:
        row = con.execute("SELECT record_json FROM loans WHERE borrower_id=? ORDER BY rowid DESC LIMIT 1", (borrower_id,)).fetchone()
    return json.loads(row[0]) if row else None


def list_loan_records() -> list[dict]:
    with _connect() as con:
        rows = con.execute("SELECT record_json FROM loans ORDER BY rowid DESC").fetchall()
    return [json.loads(row[0]) for row in rows]


def list_source_records() -> list[dict]:
    with _connect() as con:
        return [json.loads(row[0]) for row in con.execute("SELECT record_json FROM data_sources ORDER BY source_id")]


def _canonical_json(value: dict) -> str:
    """Stable JSON representation used by persisted snapshot content hashes."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _snapshot_content_hash(result: dict) -> str:
    # Transport/storage metadata is deliberately excluded from deterministic content.
    content = {key: value for key, value in result.items()
               if key not in {"created_at", "result_hash", "snapshot_freshness", "snapshot_stale_reasons"}}
    return hashlib.sha256(_canonical_json(content).encode("utf-8")).hexdigest()


def save_scenario(scenario_id: str, borrower_id: str, input_hash: str, request: dict, result: dict) -> dict:
    with _connect() as con:
        for warning in result.get("debt_warnings", []):
            record = warning.get("evidence_record", {})
            key = warning.get("derivation_key")
            if key:
                inserted = con.execute("""INSERT OR IGNORE INTO warning_evidence
                    (derivation_key, assessment_id, rule, rule_version, evidence_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (key, record.get("assessment_id", scenario_id), warning.get("id", "unknown"),
                     warning.get("rule_version", "unknown"), _canonical_json({"warning": warning, "record": record}),
                     datetime.now(timezone.utc).isoformat())).rowcount
                now = datetime.now(timezone.utc).isoformat()
                task_inserted = con.execute("INSERT OR IGNORE INTO warning_tasks VALUES (?, 'open', NULL, ?, ?)", (key, now, now)).rowcount
                if inserted or task_inserted:
                    con.execute("INSERT OR IGNORE INTO warning_task_events VALUES (?, ?, 'created', 'system', 'F7 evidence persisted', NULL, NULL, ?)",
                                ("WE-" + uuid4().hex, key, now))
        existing = con.execute("SELECT 1 FROM scenario_snapshots WHERE scenario_id=?", (scenario_id,)).fetchone()
        if existing is None:
            prior_rows = con.execute("SELECT scenario_id, request_json FROM scenario_snapshots WHERE borrower_id=? ORDER BY created_at DESC", (borrower_id,)).fetchall()
            supersedes_id = next((row["scenario_id"] for row in prior_rows
                if json.loads(row["request_json"]).get("action_id", "none") == request.get("action_id", "none")), None)
            if supersedes_id and supersedes_id != scenario_id:
                con.execute("INSERT OR IGNORE INTO scenario_supersessions VALUES (?, ?, ?)",
                    (scenario_id, supersedes_id, datetime.now(timezone.utc).isoformat()))
        con.execute("""INSERT INTO scenario_snapshots
            (scenario_id, borrower_id, input_hash, request_json, result_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(scenario_id) DO NOTHING""",
            (scenario_id, borrower_id, input_hash, _canonical_json(request),
             _canonical_json(result), datetime.now(timezone.utc).isoformat()))
        row = con.execute("SELECT result_json, created_at FROM scenario_snapshots WHERE scenario_id=?", (scenario_id,)).fetchone()
        supersession = con.execute("SELECT supersedes_id FROM scenario_supersessions WHERE scenario_id=?", (scenario_id,)).fetchone()
    stored = json.loads(row["result_json"])
    stored["created_at"] = row["created_at"]
    stored["result_hash"] = _snapshot_content_hash(stored)
    if supersession:
        stored["supersedes_id"] = supersession["supersedes_id"]
    return stored


def list_warning_evidence(limit: int = 200) -> list[dict]:
    """F7 immutable derivation evidence feed; F9 may layer assignment and lifecycle state."""
    with _connect() as con:
        rows = con.execute("SELECT * FROM warning_evidence ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [{"derivation_key": row["derivation_key"], "assessment_id": row["assessment_id"],
             "rule": row["rule"], "rule_version": row["rule_version"],
             "created_at": row["created_at"], **json.loads(row["evidence_json"])} for row in rows]


def get_warning_evidence(derivation_key: str) -> dict | None:
    with _connect() as con:
        row = con.execute("SELECT * FROM warning_evidence WHERE derivation_key=?", (derivation_key,)).fetchone()
    if row is None:
        return None
    return {"derivation_key": row["derivation_key"], "assessment_id": row["assessment_id"],
            "rule": row["rule"], "rule_version": row["rule_version"], "created_at": row["created_at"],
            **json.loads(row["evidence_json"])}


def get_warning_task(derivation_key: str) -> dict | None:
    with _connect() as con:
        task = con.execute("SELECT * FROM warning_tasks WHERE derivation_key=?", (derivation_key,)).fetchone()
        events = con.execute("SELECT * FROM warning_task_events WHERE derivation_key=? ORDER BY created_at, event_id", (derivation_key,)).fetchall()
    if task is None:
        return None
    return {"derivation_key": task["derivation_key"], "status": task["status"], "assigned_to": task["assigned_to"],
            "created_at": task["created_at"], "updated_at": task["updated_at"],
            "history": [dict(row) for row in events]}


def ensure_warning_task(derivation_key: str) -> dict | None:
    evidence = get_warning_evidence(derivation_key)
    if evidence is None:
        return None
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as con:
        inserted = con.execute("INSERT OR IGNORE INTO warning_tasks VALUES (?, 'open', NULL, ?, ?)",
                               (derivation_key, now, now)).rowcount
        if inserted:
            con.execute("INSERT INTO warning_task_events VALUES (?, ?, 'created', 'system', 'Task created from persisted F7 evidence', NULL, NULL, ?)",
                        ("WE-" + uuid4().hex, derivation_key, now))
    return get_warning_task(derivation_key)


def transition_warning_task(derivation_key: str, *, operation: str, actor: str, reason: str,
                            assigned_to: str | None = None, superseded_by: str | None = None) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    transitions = {
        "open": {"assign": "assigned", "acknowledge": "acknowledged", "resolve": "resolved", "supersede": "superseded"},
        "assigned": {"assign": "assigned", "acknowledge": "acknowledged", "resolve": "resolved", "supersede": "superseded"},
        "acknowledged": {"assign": "assigned", "resolve": "resolved", "reopen": "reopened", "supersede": "superseded"},
        "resolved": {"reopen": "reopened", "supersede": "superseded"},
        "reopened": {"assign": "assigned", "acknowledge": "acknowledged", "resolve": "resolved", "supersede": "superseded"},
        "superseded": {},
    }
    with _connect() as con:
        row = con.execute("SELECT status, assigned_to FROM warning_tasks WHERE derivation_key=?", (derivation_key,)).fetchone()
        if row is None:
            raise KeyError("Warning task not found")
        if operation not in transitions.get(row["status"], {}):
            raise ValueError(f"Invalid warning workflow transition: {row['status']} -> {operation}")
        if operation == "assign" and not (assigned_to and assigned_to.strip()):
            raise ValueError("Assignment requires an assignee")
        if operation == "supersede":
            if not superseded_by or superseded_by == derivation_key:
                raise ValueError("Supersede requires a different warning derivation key")
            old = con.execute("SELECT rule FROM warning_evidence WHERE derivation_key=?", (derivation_key,)).fetchone()
            new = con.execute("SELECT rule FROM warning_evidence WHERE derivation_key=?", (superseded_by,)).fetchone()
            if new is None or old["rule"] != new["rule"]:
                raise ValueError("Replacement warning evidence must exist and use the same rule")
        status = transitions[row["status"]][operation]
        next_assignee = assigned_to.strip() if operation == "assign" and assigned_to else (None if operation == "reopen" else row["assigned_to"])
        con.execute("UPDATE warning_tasks SET status=?, assigned_to=?, updated_at=? WHERE derivation_key=?",
                    (status, next_assignee, now, derivation_key))
        con.execute("INSERT INTO warning_task_events VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    ("WE-" + uuid4().hex, derivation_key, operation, actor, reason,
                     assigned_to if operation == "assign" else None, superseded_by, now))
    return get_warning_task(derivation_key)


def save_allocation_snapshot(allocation_id: str, branch_id: str, input_snapshot: dict, result_snapshot: dict) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as con:
        con.execute("INSERT OR IGNORE INTO allocation_snapshots VALUES (?, ?, ?, ?, ?)",
            (allocation_id, branch_id, _canonical_json(input_snapshot), _canonical_json(result_snapshot), now))
        row = con.execute("SELECT * FROM allocation_snapshots WHERE allocation_id=?", (allocation_id,)).fetchone()
    return {"allocation_id": row["allocation_id"], "branch_id": row["branch_id"],
            "input_snapshot": json.loads(row["input_json"]), "result_snapshot": json.loads(row["result_json"]),
            "created_at": row["created_at"]}


def get_allocation_snapshot(allocation_id: str) -> dict | None:
    with _connect() as con:
        row = con.execute("SELECT * FROM allocation_snapshots WHERE allocation_id=?", (allocation_id,)).fetchone()
    if row is None:
        return None
    return {"allocation_id": row["allocation_id"], "branch_id": row["branch_id"],
            "input_snapshot": json.loads(row["input_json"]), "result_snapshot": json.loads(row["result_json"]),
            "created_at": row["created_at"]}


def list_allocation_snapshots(branch_id: str | None = None, limit: int = 50) -> list[dict]:
    with _connect() as con:
        if branch_id:
            rows = con.execute("SELECT allocation_id FROM allocation_snapshots WHERE branch_id=? ORDER BY created_at DESC LIMIT ?",
                               (branch_id, max(1, min(limit, 250)))).fetchall()
        else:
            rows = con.execute("SELECT allocation_id FROM allocation_snapshots ORDER BY created_at DESC LIMIT ?",
                               (max(1, min(limit, 250)),)).fetchall()
    return [get_allocation_snapshot(row[0]) for row in rows]


def create_intervention_proposal(*, comparison_id: str, candidate_id: str, assessment_id: str,
                                 scenario_id: str, actor: str, reason: str) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    proposal_id = "IP-" + uuid4().hex[:16].upper()
    history = [{"status": "proposed", "actor": actor, "reason": reason, "assessment_id": assessment_id,
                "at": now, "event": "proposal_created"}]
    with _connect() as con:
        con.execute("""INSERT INTO intervention_proposals
            (proposal_id, comparison_id, candidate_id, assessment_id, scenario_id, status, created_at, updated_at,
             review_history_json, applied_simulation_json) VALUES (?, ?, ?, ?, ?, 'proposed', ?, ?, ?, NULL)""",
            (proposal_id, comparison_id, candidate_id, assessment_id, scenario_id, now, now, _canonical_json(history)))
    return get_intervention_proposal(proposal_id)


def get_intervention_proposal(proposal_id: str) -> dict | None:
    with _connect() as con:
        row = con.execute("SELECT * FROM intervention_proposals WHERE proposal_id=?", (proposal_id,)).fetchone()
    if row is None:
        return None
    return {"proposal_id": row["proposal_id"], "comparison_id": row["comparison_id"],
            "candidate_id": row["candidate_id"], "assessment_id": row["assessment_id"],
            "scenario_id": row["scenario_id"], "status": row["status"], "created_at": row["created_at"],
            "updated_at": row["updated_at"], "review_history": json.loads(row["review_history_json"]),
            "applied_simulation": json.loads(row["applied_simulation_json"]) if row["applied_simulation_json"] else None}


def list_intervention_proposals(limit: int = 100) -> list[dict]:
    with _connect() as con:
        ids = [row[0] for row in con.execute("SELECT proposal_id FROM intervention_proposals ORDER BY created_at DESC LIMIT ?", (max(1, min(limit, 250)),))]
    return [get_intervention_proposal(proposal_id) for proposal_id in ids]


def transition_intervention_proposal(proposal_id: str, *, status: str, actor: str, reason: str,
                                     allowed_transitions: dict, applied_simulation: dict | None = None) -> dict | None:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as con:
        row = con.execute("SELECT * FROM intervention_proposals WHERE proposal_id=?", (proposal_id,)).fetchone()
        if row is None:
            return None
        old_status = row["status"]
        if status not in allowed_transitions.get(old_status, []):
            raise ValueError(f"Invalid intervention review transition: {old_status} -> {status}")
        history = json.loads(row["review_history_json"])
        history.append({"status": status, "actor": actor, "reason": reason,
                        "assessment_id": row["assessment_id"], "at": now, "event": "review_transition"})
        con.execute("""UPDATE intervention_proposals SET status=?, updated_at=?, review_history_json=?, applied_simulation_json=?
            WHERE proposal_id=? AND status=?""",
            (status, now, _canonical_json(history), _canonical_json(applied_simulation) if applied_simulation else row["applied_simulation_json"], proposal_id, old_status))
    return get_intervention_proposal(proposal_id)


def get_scenario(scenario_id: str) -> dict | None:
    with _connect() as con:
        row = con.execute("SELECT result_json, request_json, created_at FROM scenario_snapshots WHERE scenario_id=?", (scenario_id,)).fetchone()
    if not row:
        return None
    result = json.loads(row["result_json"])
    result["created_at"] = row["created_at"]
    result["result_hash"] = _snapshot_content_hash(result)
    with _connect() as con:
        supersession = con.execute("SELECT supersedes_id FROM scenario_supersessions WHERE scenario_id=?", (scenario_id,)).fetchone()
    if supersession:
        result["supersedes_id"] = supersession["supersedes_id"]
    # Earlier snapshots predate the request echo used by the reopen UI. Keep
    # immutable results intact and fill that UI-only field from the stored request.
    from app.schemas import ScenarioRequest
    stored_request = result.get("scenario_request") or json.loads(row["request_json"])
    result["scenario_request"] = ScenarioRequest.model_validate(stored_request).model_dump(mode="json")
    from app.config import ENGINE_VERSION
    reasons = []
    current_borrower = get_borrower_record(result["borrower_id"])
    frozen_borrower = result.get("frozen_context", {}).get("borrower")
    if current_borrower and frozen_borrower and "posted_loan_events" in frozen_borrower:
        linked_loan = get_loan_record(result["borrower_id"])
        as_of = date.fromisoformat(result["assessment_as_of"])
        current_borrower["posted_loan_events"] = [event for event in (linked_loan or {}).get("posted_events", [])
                                                    if date.fromisoformat(event["date"]) <= as_of]
    # An application assessment can model a requested principal before the
    # borrower profile is updated on demo approval. That proposal is part of
    # the immutable scenario input, not evidence that its profile went stale.
    principal_override = result["scenario_request"].get("loan_principal_override_inr")
    if current_borrower and principal_override is not None:
        current_borrower["loan_principal_inr"] = str(Decimal(principal_override))
    current_borrower_cmp = {k: v for k, v in current_borrower.items() if k != "posted_loan_events"} if current_borrower else None
    frozen_borrower_cmp = {k: v for k, v in frozen_borrower.items() if k != "posted_loan_events"} if frozen_borrower else None
    if current_borrower_cmp and frozen_borrower_cmp and json.dumps(current_borrower_cmp, sort_keys=True) != json.dumps(frozen_borrower_cmp, sort_keys=True):
        reasons.append("borrower_profile_changed")
    versions = result.get("source_versions", {})
    if versions.get("engine") != ENGINE_VERSION:
        reasons.append("engine_version_changed")
    weather_path = Path(__file__).resolve().parents[2] / "data" / "raw" / "open_meteo" / "pune_kharif_2015_era5.json"
    frozen_weather_hash = versions.get("weather_snapshot_hash")
    if frozen_weather_hash and weather_path.exists():
        current_weather_hash = hashlib.sha256(weather_path.read_bytes()).hexdigest()
        if frozen_weather_hash != current_weather_hash:
            reasons.append("source_snapshot_changed")
    result["snapshot_freshness"] = "stale" if reasons else "current"
    result["snapshot_stale_reasons"] = reasons
    with _connect() as con:
        bundle_rows = con.execute("SELECT bundle_id, bundle_json FROM comparison_bundles ORDER BY created_at DESC").fetchall()
    for bundle_row in bundle_rows:
        refs = json.loads(bundle_row["bundle_json"])
        linked_ids = {refs["baseline_ref"]["scenario_id"], refs["stress_ref"]["scenario_id"],
                      *[item["scenario_id"] for item in refs["candidate_refs"]]}
        if scenario_id in linked_ids:
            result["comparison_bundle_id"] = bundle_row["bundle_id"]
            break
    return result


def save_comparison_bundle(bundle: dict) -> dict:
    content = {key: value for key, value in bundle.items() if key not in {"created_at", "bundle_hash", "bundle_id"}}
    bundle_hash = hashlib.sha256(_canonical_json(content).encode("utf-8")).hexdigest()
    bundle_id = bundle_hash[:24]
    with _connect() as con:
        exists = con.execute("SELECT 1 FROM comparison_bundles WHERE bundle_id=?", (bundle_id,)).fetchone()
        if exists is None:
            prior = con.execute("SELECT bundle_id, bundle_json FROM comparison_bundles ORDER BY created_at DESC").fetchall()
            supersedes = next((row["bundle_id"] for row in prior
                if json.loads(row["bundle_json"]).get("borrower_id") == bundle.get("borrower_id")), None)
            if supersedes:
                con.execute("INSERT OR IGNORE INTO comparison_bundle_supersessions VALUES (?, ?, ?)",
                    (bundle_id, supersedes, datetime.now(timezone.utc).isoformat()))
        con.execute("""INSERT INTO comparison_bundles (bundle_id, context_hash, bundle_json, created_at)
            VALUES (?, ?, ?, ?) ON CONFLICT(bundle_id) DO NOTHING""",
            (bundle_id, bundle["comparison_context_hash"], _canonical_json(content), datetime.now(timezone.utc).isoformat()))
        row = con.execute("SELECT bundle_json, created_at FROM comparison_bundles WHERE bundle_id=?", (bundle_id,)).fetchone()
        supersession = con.execute("SELECT supersedes_bundle_id FROM comparison_bundle_supersessions WHERE bundle_id=?", (bundle_id,)).fetchone()
    saved = json.loads(row["bundle_json"])
    saved["bundle_id"] = bundle_id
    saved["created_at"] = row["created_at"]
    saved["bundle_hash"] = bundle_hash
    if supersession:
        saved["supersedes_bundle_id"] = supersession["supersedes_bundle_id"]
    return saved


def get_comparison_bundle(bundle_id: str) -> dict | None:
    with _connect() as con:
        row = con.execute("SELECT bundle_json, created_at FROM comparison_bundles WHERE bundle_id=?", (bundle_id,)).fetchone()
        supersession = con.execute("SELECT supersedes_bundle_id FROM comparison_bundle_supersessions WHERE bundle_id=?", (bundle_id,)).fetchone()
    if not row:
        return None
    saved = json.loads(row["bundle_json"])
    saved["bundle_id"] = bundle_id
    saved["created_at"] = row["created_at"]
    content = {key: value for key, value in saved.items() if key not in {"created_at", "bundle_hash", "bundle_id"}}
    saved["bundle_hash"] = hashlib.sha256(_canonical_json(content).encode("utf-8")).hexdigest()
    if supersession:
        saved["supersedes_bundle_id"] = supersession["supersedes_bundle_id"]
    return saved


def list_comparison_bundles(limit: int = 100) -> list[dict]:
    with _connect() as con:
        ids = [row[0] for row in con.execute("SELECT bundle_id FROM comparison_bundles ORDER BY created_at DESC LIMIT ?",
                                             (max(1, min(limit, 500)),))]
    return [get_comparison_bundle(bundle_id) for bundle_id in ids]


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
