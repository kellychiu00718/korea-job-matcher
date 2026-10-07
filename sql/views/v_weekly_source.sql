DROP VIEW IF EXISTS v_weekly_source;
CREATE VIEW v_weekly_source AS
SELECT
    source,
    COUNT(*) AS total,
    SUM(CASE WHEN prefilter_passed = 1 THEN 1 ELSE 0 END) AS passed_prefilter,
    SUM(CASE WHEN ai_match_score >= 40 THEN 1 ELSE 0 END) AS recommended,
    ROUND(AVG(ai_match_score), 1) AS avg_score,
    ROUND(AVG(CASE WHEN posted_date != '' THEN julianday('now') - julianday(posted_date) END), 1) AS avg_posting_days
FROM seen_jobs
WHERE first_seen >= date('now', '-7 days')
GROUP BY source;
