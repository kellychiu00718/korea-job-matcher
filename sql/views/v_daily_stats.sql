DROP VIEW IF EXISTS v_daily_stats;
CREATE VIEW v_daily_stats AS
SELECT
    run_date, jobs_scraped, jobs_new, jobs_matched, jobs_enriched,
    jobs_recommended, jobs_prefilter_passed, recommendation_rate,
    api_cost_usd, errors, duration_seconds
FROM pipeline_runs
ORDER BY run_date DESC;
