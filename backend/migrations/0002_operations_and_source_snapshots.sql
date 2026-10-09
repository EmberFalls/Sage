CREATE TABLE IF NOT EXISTS applications (
    application_id TEXT PRIMARY KEY,
    borrower_id TEXT NOT NULL,
    status TEXT NOT NULL,
    record_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(borrower_id) REFERENCES borrowers(borrower_id)
);

CREATE INDEX IF NOT EXISTS idx_applications_created
    ON applications(created_at DESC, application_id DESC);

CREATE TABLE IF NOT EXISTS source_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    record_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_source_snapshots_latest
    ON source_snapshots(source_id, retrieved_at DESC);
