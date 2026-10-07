CREATE TABLE IF NOT EXISTS company_cache (
    normalized_name TEXT PRIMARY KEY,
    company_type TEXT NOT NULL,
    confidence TEXT NOT NULL,
    source TEXT NOT NULL,
    verified_at TEXT NOT NULL,
    raw_search_snippet TEXT DEFAULT ''
);
