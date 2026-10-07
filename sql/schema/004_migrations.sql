-- seen_jobs migrations (idempotent — run via ALTER TABLE ADD COLUMN with try/except)
-- Each line: column_name|column_def
-- Parsed by Python, not executed as raw SQL

-- Original migration columns
location|TEXT DEFAULT ''
experience_required|TEXT DEFAULT ''
salary_info|TEXT DEFAULT ''
posted_date|TEXT DEFAULT ''
deadline|TEXT DEFAULT ''
jd_text|TEXT DEFAULT ''
jd_language|TEXT DEFAULT ''
company_type|TEXT DEFAULT ''
scraped_at|TEXT DEFAULT ''
keyword_score|REAL DEFAULT 0
ai_match_score|REAL DEFAULT 0
match_reasons|TEXT DEFAULT ''
positioning_advice|TEXT DEFAULT ''
company_intro|TEXT DEFAULT ''
products_services|TEXT DEFAULT ''
business_model|TEXT DEFAULT ''
vision_goals|TEXT DEFAULT ''
ideal_candidate|TEXT DEFAULT ''
market_position|TEXT DEFAULT ''
team_function|TEXT DEFAULT ''
linkedin_search_url|TEXT DEFAULT ''
connect_message_draft|TEXT DEFAULT ''
coffee_chat_draft|TEXT DEFAULT ''
freshness_label|TEXT DEFAULT ''

-- Phase 2 new columns
company_type_confidence|TEXT DEFAULT 'unverified'
company_type_source|TEXT DEFAULT ''
canonical_key|TEXT DEFAULT ''
canonical_group_id|TEXT DEFAULT ''
effective_date|TEXT DEFAULT ''
ranking_score|REAL DEFAULT 0
prefilter_passed|INTEGER DEFAULT 0
