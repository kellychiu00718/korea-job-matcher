DROP VIEW IF EXISTS v_weekly_trends;
CREATE VIEW v_weekly_trends AS
SELECT
    'total_scraped' AS metric,
    COALESCE(this.val, 0) AS this_week,
    COALESCE(prev.val, 0) AS prev_week,
    CASE WHEN COALESCE(prev.val, 0) > 0
         THEN ROUND(100.0 * (COALESCE(this.val, 0) - prev.val) / prev.val, 1)
         ELSE NULL END AS change_pct,
    CASE WHEN COALESCE(this.val, 0) > COALESCE(prev.val, 0) THEN 'up'
         WHEN COALESCE(this.val, 0) < COALESCE(prev.val, 0) THEN 'down'
         ELSE 'flat' END AS direction
FROM (SELECT SUM(jobs_scraped) AS val FROM pipeline_runs WHERE run_date >= date('now', '-7 days')) this,
     (SELECT SUM(jobs_scraped) AS val FROM pipeline_runs WHERE run_date >= date('now', '-14 days') AND run_date < date('now', '-7 days')) prev

UNION ALL

SELECT
    'unique_new',
    COALESCE(this.val, 0), COALESCE(prev.val, 0),
    CASE WHEN COALESCE(prev.val, 0) > 0
         THEN ROUND(100.0 * (COALESCE(this.val, 0) - prev.val) / prev.val, 1)
         ELSE NULL END,
    CASE WHEN COALESCE(this.val, 0) > COALESCE(prev.val, 0) THEN 'up'
         WHEN COALESCE(this.val, 0) < COALESCE(prev.val, 0) THEN 'down'
         ELSE 'flat' END
FROM (SELECT SUM(jobs_new) AS val FROM pipeline_runs WHERE run_date >= date('now', '-7 days')) this,
     (SELECT SUM(jobs_new) AS val FROM pipeline_runs WHERE run_date >= date('now', '-14 days') AND run_date < date('now', '-7 days')) prev

UNION ALL

SELECT
    'recommended',
    COALESCE(this.val, 0), COALESCE(prev.val, 0),
    CASE WHEN COALESCE(prev.val, 0) > 0
         THEN ROUND(100.0 * (COALESCE(this.val, 0) - prev.val) / prev.val, 1)
         ELSE NULL END,
    CASE WHEN COALESCE(this.val, 0) > COALESCE(prev.val, 0) THEN 'up'
         WHEN COALESCE(this.val, 0) < COALESCE(prev.val, 0) THEN 'down'
         ELSE 'flat' END
FROM (SELECT SUM(jobs_recommended) AS val FROM pipeline_runs WHERE run_date >= date('now', '-7 days')) this,
     (SELECT SUM(jobs_recommended) AS val FROM pipeline_runs WHERE run_date >= date('now', '-14 days') AND run_date < date('now', '-7 days')) prev

UNION ALL

SELECT
    'avg_score',
    COALESCE(this.val, 0), COALESCE(prev.val, 0),
    CASE WHEN COALESCE(prev.val, 0) > 0
         THEN ROUND(100.0 * (COALESCE(this.val, 0) - prev.val) / prev.val, 1)
         ELSE NULL END,
    CASE WHEN COALESCE(this.val, 0) > COALESCE(prev.val, 0) THEN 'up'
         WHEN COALESCE(this.val, 0) < COALESCE(prev.val, 0) THEN 'down'
         ELSE 'flat' END
FROM (SELECT ROUND(AVG(ai_match_score), 1) AS val FROM seen_jobs WHERE first_seen >= date('now', '-7 days') AND ai_match_score > 0) this,
     (SELECT ROUND(AVG(ai_match_score), 1) AS val FROM seen_jobs WHERE first_seen >= date('now', '-14 days') AND first_seen < date('now', '-7 days') AND ai_match_score > 0) prev;
