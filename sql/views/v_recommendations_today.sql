DROP VIEW IF EXISTS v_recommendations_today;
CREATE VIEW v_recommendations_today AS
SELECT
    dedup_key, source, title, company, company_type,
    company_type_confidence, location, experience_required,
    salary_info, posted_date, deadline, jd_language,
    ai_match_score, ranking_score, match_reasons, positioning_advice,
    company_intro, products_services, business_model, vision_goals,
    ideal_candidate, market_position, team_function,
    linkedin_search_url, url, freshness_label
FROM seen_jobs
WHERE ai_match_score >= 40
  AND last_seen >= date('now')
ORDER BY ranking_score DESC
LIMIT 10;
