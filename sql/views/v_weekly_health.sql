DROP VIEW IF EXISTS v_weekly_health;
CREATE VIEW v_weekly_health AS
SELECT
    SUM(jobs_scraped) AS total_scraped,
    SUM(jobs_new) AS unique_new,
    SUM(jobs_prefilter_passed) AS prefilter_passed,
    SUM(jobs_recommended) AS recommended,
    ROUND(
        CASE WHEN SUM(jobs_new) > 0
             THEN 1.0 * SUM(jobs_prefilter_passed) / SUM(jobs_new)
             ELSE 0 END, 3
    ) AS prefilter_rate,
    ROUND(
        CASE WHEN SUM(jobs_new) > 0
             THEN 1.0 * SUM(jobs_recommended) / SUM(jobs_new)
             ELSE 0 END, 3
    ) AS recommendation_rate,
    ROUND(AVG(duration_seconds), 1) AS avg_duration_seconds,
    ROUND(SUM(api_cost_usd), 4) AS total_api_cost,
    COUNT(*) AS total_runs,
    SUM(CASE WHEN errors != '' THEN 1 ELSE 0 END) AS error_runs,
    GROUP_CONCAT(
        CASE WHEN errors != '' THEN errors END, '; '
    ) AS failed_sources
FROM pipeline_runs
WHERE run_date >= date('now', '-7 days');
