DROP VIEW IF EXISTS v_weekly_company_type;
CREATE VIEW v_weekly_company_type AS
SELECT
    company_type,
    company_type_confidence AS confidence,
    COUNT(*) AS job_count,
    ROUND(AVG(ai_match_score), 1) AS avg_ai_score,
    ROUND(
        100.0 * SUM(CASE WHEN ai_match_score >= 40 THEN 1 ELSE 0 END) / COUNT(*), 1
    ) AS pct_recommended
FROM seen_jobs
WHERE first_seen >= date('now', '-7 days')
  AND company_type != ''
GROUP BY company_type, company_type_confidence
ORDER BY avg_ai_score DESC;
