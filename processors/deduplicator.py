import logging
import sqlite3
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "jobs.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _parse_migration_file(filename: str) -> list[tuple[str, str]]:
    from sql.loader import load_sql
    text = load_sql(filename)
    columns = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("--"):
            continue
        parts = line.split("|", 1)
        if len(parts) == 2:
            columns.append((parts[0].strip(), parts[1].strip()))
    return columns


def init_db():
    from sql.loader import load_sql, load_all_in

    conn = get_connection()

    conn.executescript(load_sql("001_seen_jobs"))
    conn.executescript(load_sql("002_pipeline_runs"))
    conn.executescript(load_sql("005_company_cache"))

    for col_name, col_def in _parse_migration_file("004_migrations"):
        try:
            conn.execute(f"ALTER TABLE seen_jobs ADD COLUMN {col_name} {col_def}")
        except sqlite3.OperationalError:
            pass

    for col_name, col_def in _parse_migration_file("006_pipeline_runs_migrations"):
        try:
            conn.execute(f"ALTER TABLE pipeline_runs ADD COLUMN {col_name} {col_def}")
        except sqlite3.OperationalError:
            pass

    conn.executescript(load_sql("003_indexes"))

    for _name, sql in load_all_in("views"):
        conn.executescript(sql)

    conn.commit()
    conn.close()


def is_new_job(dedup_key: str) -> bool:
    from sql import load_sql
    conn = get_connection()
    row = conn.execute(load_sql("is_new_job"), (dedup_key,)).fetchone()
    conn.close()
    return row is None


def mark_seen(job) -> bool:
    from sql import load_sql
    conn = get_connection()
    now = datetime.now().isoformat()
    try:
        conn.execute(load_sql("mark_seen"),
                     (job.dedup_key, job.source, job.source_id, job.title,
                      job.company, job.url, now, now))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.execute(load_sql("mark_seen_update"), (now, job.dedup_key))
        conn.commit()
        conn.close()
        return False


def upsert_job(job):
    from sql import load_sql
    conn = get_connection()
    now = datetime.now().isoformat()
    conn.execute(load_sql("upsert_job"), (
        job.location, job.experience_required, job.salary_info,
        job.posted_date, job.deadline, (job.jd_text or "")[:5000],
        job.jd_language, job.company_type, job.scraped_at,
        job.keyword_score, job.ai_match_score, job.ai_match_score,
        job.match_reasons, job.positioning_advice,
        job.company_intro, job.products_services,
        job.business_model, job.vision_goals,
        job.ideal_candidate, job.market_position,
        job.team_function, job.linkedin_search_url,
        job.connect_message_draft, job.coffee_chat_draft,
        job.freshness_label,
        getattr(job, 'company_type_confidence', 'unverified'),
        getattr(job, 'company_type_source', ''),
        getattr(job, 'canonical_key', ''),
        getattr(job, 'canonical_group_id', ''),
        getattr(job, 'effective_date', '') or (job.posted_date or job.scraped_at),
        getattr(job, 'ranking_score', 0.0),
        getattr(job, 'prefilter_passed', 0),
        now,
        job.dedup_key,
    ))
    conn.commit()
    conn.close()


def update_score(dedup_key: str, score: float):
    from sql import load_sql
    conn = get_connection()
    conn.execute(load_sql("update_score"), (score, dedup_key))
    conn.commit()
    conn.close()


def log_run(jobs_scraped: int, jobs_new: int, jobs_matched: int,
            jobs_enriched: int, api_cost: float, errors: str,
            duration: float, jobs_recommended: int = 0,
            jobs_prefilter_passed: int = 0):
    from sql import load_sql
    conn = get_connection()
    recommendation_rate = (jobs_recommended / jobs_new) if jobs_new > 0 else 0.0
    conn.execute(load_sql("log_run"),
                 (datetime.now().isoformat(), jobs_scraped, jobs_new,
                  jobs_matched, jobs_enriched, jobs_recommended,
                  jobs_prefilter_passed, recommendation_rate,
                  api_cost, errors, duration))
    conn.commit()
    conn.close()


def get_api_cost_today() -> float:
    from sql import load_sql
    conn = get_connection()
    today = datetime.now().strftime("%Y-%m-%d")
    row = conn.execute(load_sql("api_cost_today"), (f"{today}%",)).fetchone()
    conn.close()
    return row[0] if row else 0.0
