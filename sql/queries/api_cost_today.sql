SELECT COALESCE(SUM(api_cost_usd), 0) FROM pipeline_runs WHERE run_date LIKE ?;
