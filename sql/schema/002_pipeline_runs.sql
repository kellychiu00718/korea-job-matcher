CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT NOT NULL,
    jobs_scraped INTEGER DEFAULT 0,
    jobs_new INTEGER DEFAULT 0,
    jobs_matched INTEGER DEFAULT 0,
    jobs_enriched INTEGER DEFAULT 0,
    api_cost_usd REAL DEFAULT 0,
    errors TEXT DEFAULT '',
    duration_seconds REAL DEFAULT 0
);
