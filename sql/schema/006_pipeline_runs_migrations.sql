-- pipeline_runs migrations (idempotent — parsed by Python like 004)
-- Each line: column_name|column_def

jobs_recommended|INTEGER DEFAULT 0
jobs_prefilter_passed|INTEGER DEFAULT 0
recommendation_rate|REAL DEFAULT 0
