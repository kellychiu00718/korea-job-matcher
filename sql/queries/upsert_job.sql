UPDATE seen_jobs SET
    location = ?, experience_required = ?, salary_info = ?,
    posted_date = ?, deadline = ?, jd_text = ?,
    jd_language = ?, company_type = ?, scraped_at = ?,
    keyword_score = ?, ai_match_score = ?, match_score = ?,
    match_reasons = ?, positioning_advice = ?,
    company_intro = ?, products_services = ?,
    business_model = ?, vision_goals = ?,
    ideal_candidate = ?, market_position = ?,
    team_function = ?, linkedin_search_url = ?,
    connect_message_draft = ?, coffee_chat_draft = ?,
    freshness_label = ?,
    company_type_confidence = ?, company_type_source = ?,
    canonical_key = ?, canonical_group_id = ?,
    effective_date = ?, ranking_score = ?, prefilter_passed = ?,
    last_seen = ?
WHERE dedup_key = ?;
