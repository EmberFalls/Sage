CREATE TABLE IF NOT EXISTS warning_action_events (
    event_id TEXT PRIMARY KEY,
    warning_key TEXT NOT NULL,
    scenario_id TEXT NOT NULL,
    warning_id TEXT NOT NULL,
    status TEXT NOT NULL,
    record_json TEXT NOT NULL,
    actor TEXT NOT NULL,
    assigned_to TEXT,
    rationale TEXT NOT NULL,
    created_at TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_warning_action_history
    ON warning_action_events(scenario_id, warning_key, created_at DESC);

CREATE TABLE IF NOT EXISTS portfolio_allocations (
    allocation_id TEXT PRIMARY KEY,
    budget_inr TEXT NOT NULL,
    allocated_inr TEXT NOT NULL,
    record_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_portfolio_allocations_created
    ON portfolio_allocations(created_at DESC);
