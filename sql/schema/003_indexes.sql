CREATE INDEX IF NOT EXISTS idx_seen_jobs_last_seen ON seen_jobs(last_seen);
CREATE INDEX IF NOT EXISTS idx_seen_jobs_score ON seen_jobs(match_score DESC);
CREATE INDEX IF NOT EXISTS idx_seen_jobs_company_type ON seen_jobs(company_type);
CREATE INDEX IF NOT EXISTS idx_seen_jobs_source ON seen_jobs(source);
CREATE INDEX IF NOT EXISTS idx_seen_jobs_first_seen ON seen_jobs(first_seen);
CREATE INDEX IF NOT EXISTS idx_seen_jobs_canonical ON seen_jobs(canonical_key);
