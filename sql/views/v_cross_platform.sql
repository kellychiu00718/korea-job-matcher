DROP VIEW IF EXISTS v_cross_platform;
CREATE VIEW v_cross_platform AS
SELECT
    canonical_key,
    COUNT(*) AS entry_count,
    COUNT(DISTINCT source) AS source_count,
    GROUP_CONCAT(DISTINCT source) AS sources,
    GROUP_CONCAT(DISTINCT company) AS company_variants,
    MAX(ai_match_score) AS best_score,
    MIN(first_seen) AS earliest_seen
FROM seen_jobs
WHERE canonical_key != ''
GROUP BY canonical_key
HAVING source_count > 1
ORDER BY best_score DESC;
