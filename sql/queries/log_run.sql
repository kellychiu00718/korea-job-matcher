INSERT INTO pipeline_runs
    (run_date, jobs_scraped, jobs_new, jobs_matched, jobs_enriched,
     jobs_recommended, jobs_prefilter_passed, recommendation_rate,
     api_cost_usd, errors, duration_seconds)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
