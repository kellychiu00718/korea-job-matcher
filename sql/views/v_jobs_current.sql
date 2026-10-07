DROP VIEW IF EXISTS v_jobs_current;
CREATE VIEW v_jobs_current AS
SELECT
    dedup_key, source, title, company, company_type,
    company_type_confidence, location, experience_required,
    salary_info, posted_date, deadline, jd_language,
    keyword_score, ai_match_score, ranking_score, match_reasons,
    positioning_advice, url, first_seen, last_seen,
    effective_date, freshness_label, canonical_key,
    prefilter_passed, application_status
FROM seen_jobs
WHERE first_seen >= date('now', '-30 days')
ORDER BY ai_match_score DESC;
