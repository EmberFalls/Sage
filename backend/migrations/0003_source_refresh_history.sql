CREATE TABLE IF NOT EXISTS source_refresh_events (
    refresh_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    attempted_at TEXT NOT NULL,
    status TEXT NOT NULL,
    snapshot_id TEXT,
    error_code TEXT
);

CREATE INDEX IF NOT EXISTS idx_source_refresh_latest
    ON source_refresh_events(source_id, attempted_at DESC);
