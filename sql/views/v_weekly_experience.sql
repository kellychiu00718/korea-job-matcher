DROP VIEW IF EXISTS v_weekly_experience;
CREATE VIEW v_weekly_experience AS
SELECT
    experience_required,
    COUNT(*) AS job_count,
    ROUND(AVG(ai_match_score), 1) AS avg_ai_score
FROM seen_jobs
WHERE first_seen >= date('now', '-7 days')
  AND experience_required != ''
GROUP BY experience_required
ORDER BY job_count DESC;
