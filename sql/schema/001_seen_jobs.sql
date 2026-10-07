CREATE TABLE IF NOT EXISTS seen_jobs (
    dedup_key TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    title TEXT,
    company TEXT,
    url TEXT,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    match_score REAL DEFAULT 0,
    application_status TEXT DEFAULT '',
    notes TEXT DEFAULT ''
);
