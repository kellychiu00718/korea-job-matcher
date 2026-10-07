#!/usr/bin/env python3
"""
Korea Daily Job Shortlist — daily automated job matching for Korean job boards.

Scrapes 4 platforms → dedup → canonical merge → age cutoff → company classify
→ keyword filter → AI match → enrich → SQLite → CSV → email.
"""

import logging
import os
import smtplib
import sys
import time
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from scrapers import (
    SaraminScraper,
    IncruitScraper,
    JobKoreaScraper,
    WantedScraper,
)
from processors.models import Job
from processors.deduplicator import init_db, mark_seen, update_score, upsert_job, log_run
from processors.matcher import (
    load_skill_profile,
    keyword_prefilter,
    ai_match_and_score,
    select_top_recommendations,
    apply_age_cutoff,
)
from processors.canonical import merge_cross_platform
from processors.company_classifier import CompanyClassifier
from processors.enricher import enrich_jobs
from processors.linkedin_helper import add_linkedin_info, draft_outreach_messages
from output.reporter import build_email_summary
from output.mailer import send_report
from output.csv_exporter import export_daily_csvs
from output.weekly_report import generate_weekly_report

CONFIG_PATH = Path(__file__).parent / "config" / "config.yaml"
LOG_DIR = Path(__file__).parent / "logs"
EXPORTS_DIR = Path(__file__).parent / "data" / "exports"


def send_failure_alert(error_msg: str):
    addr = os.getenv("GMAIL_ADDRESS", "")
    pwd = os.getenv("GMAIL_APP_PASSWORD", "")
    if not addr or not pwd:
        return
    try:
        msg = MIMEText(f"Job Pipeline 執行異常:\n\n{error_msg}\n\n請檢查 ~/job-pipeline/logs/")
        msg["Subject"] = "[Job Pipeline ALERT] 執行失敗"
        msg["From"] = addr
        msg["To"] = addr
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
            s.login(addr, pwd)
            s.sendmail(addr, addr, msg.as_string())
    except Exception:
        pass


def setup_logging():
    LOG_DIR.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(LOG_DIR / f"pipeline_{today}.log", encoding="utf-8"),
        ],
    )


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_pipeline():
    start_time = time.time()
    setup_logging()
    logger = logging.getLogger("pipeline")
    logger.info("=" * 60)
    logger.info("Job Pipeline started")

    config = load_config()
    profile = load_skill_profile()
    init_db()

    pipeline_cfg = config["pipeline"]
    max_per_source = pipeline_cfg["max_jobs_per_source"]
    max_recommendations = pipeline_cfg["max_daily_recommendations"]
    delay = pipeline_cfg["request_delay_seconds"]
    max_retries = pipeline_cfg["max_retries"]
    daily_budget = config["risk_management"]["daily_api_budget_usd"]

    all_keywords = config["search_keywords"]["korean"] + config["search_keywords"]["english"]

    # ── Step 1: Scrape all platforms ──
    logger.info("Step 1: Scraping job platforms...")
    scrapers = [
        SaraminScraper(delay=delay, max_retries=max_retries),
        IncruitScraper(delay=delay, max_retries=max_retries),
        JobKoreaScraper(delay=delay, max_retries=max_retries),
        WantedScraper(delay=delay, max_retries=max_retries),
    ]

    all_scraped = []
    scraper_stats = {}
    errors = []

    for scraper in scrapers:
        jobs = scraper.scrape_safe(all_keywords, max_results=max_per_source)
        scraper_stats[scraper.source_name] = len(jobs)
        all_scraped.extend(jobs)
        if len(jobs) == 0:
            errors.append(f"{scraper.source_name}: zero results")

    total_scraped = len(all_scraped)
    logger.info(f"Total scraped: {total_scraped} jobs across {len(scrapers)} platforms")

    # ── Step 2: Platform dedup ──
    logger.info("Step 2: Deduplicating...")
    new_jobs = []
    for job in all_scraped:
        if mark_seen(job):
            new_jobs.append(job)

    logger.info(f"New jobs: {len(new_jobs)} (filtered {total_scraped - len(new_jobs)} duplicates)")

    if not new_jobs:
        logger.info("No new jobs today. Sending summary email.")
        summary = build_email_summary([], 0, scraper_stats)
        csv_path = EXPORTS_DIR / "recommendations_today.csv"
        send_report(csv_path, summary, 0, 0)
        duration = time.time() - start_time
        log_run(total_scraped, 0, 0, 0, 0.0, "; ".join(errors), duration, 0, 0)
        return

    # ── Step 3: Cross-platform canonical dedup ──
    logger.info("Step 3: Cross-platform dedup...")
    new_jobs = merge_cross_platform(new_jobs)
    logger.info(f"After canonical merge: {len(new_jobs)} jobs")

    # ── Step 4: Age cutoff (>30 days) ──
    logger.info("Step 4: Age cutoff...")
    before_cutoff = len(new_jobs)
    new_jobs = apply_age_cutoff(new_jobs, max_days=30)
    logger.info(f"After age cutoff: {len(new_jobs)} (removed {before_cutoff - len(new_jobs)} old jobs)")

    # ── Step 5: Company classification ──
    logger.info("Step 5: Classifying companies...")
    tavily_key = os.getenv("TAVILY_API_KEY", "")
    classifier = CompanyClassifier(tavily_key=tavily_key, max_daily_searches=20)
    classifier.classify_batch(new_jobs)

    # ── Step 6: Detect language ──
    for job in new_jobs:
        job.jd_language = job.detect_jd_language()
        job.effective_date = job.posted_date or job.scraped_at

    # ── Step 7: Keyword pre-filter ──
    logger.info("Step 6: Keyword pre-filtering...")
    filtered = keyword_prefilter(new_jobs, profile, min_score=2.0)
    logger.info(f"Passed keyword filter: {len(filtered)} jobs")

    if not filtered:
        logger.info("No jobs passed keyword filter.")
        for job in new_jobs:
            upsert_job(job)
        summary = build_email_summary([], len(new_jobs), scraper_stats)
        export_daily_csvs()
        csv_path = EXPORTS_DIR / "recommendations_today.csv"
        send_report(csv_path, summary, 0, 0)
        duration = time.time() - start_time
        log_run(total_scraped, len(new_jobs), 0, 0, 0.0, "; ".join(errors), duration, 0, 0)
        return

    # ── Step 8: AI matching ──
    logger.info("Step 7: AI matching & scoring...")
    total_api_cost = 0.0

    result = ai_match_and_score(filtered, profile, max_daily_budget=daily_budget)
    if isinstance(result, tuple):
        scored_jobs, match_cost = result
    else:
        scored_jobs, match_cost = result, 0.0
    total_api_cost += match_cost

    for job in scored_jobs:
        update_score(job.dedup_key, job.ai_match_score)

    # ── Step 9: Select top recommendations (max 10) ──
    recommendations = select_top_recommendations(scored_jobs, max_count=max_recommendations)
    logger.info(f"Top recommendations: {len(recommendations)} jobs")

    # ── Step 10: Enrich high-score jobs ──
    logger.info("Step 8: Enriching top recommendations...")
    remaining_budget = max(0, daily_budget - total_api_cost)
    recommendations, enrich_cost = enrich_jobs(recommendations, profile, max_budget=remaining_budget)
    total_api_cost += enrich_cost

    # ── Step 11: LinkedIn helper ──
    logger.info("Step 9: Generating LinkedIn info & outreach drafts...")
    recommendations = add_linkedin_info(recommendations)
    remaining_budget = max(0, daily_budget - total_api_cost)
    if remaining_budget > 0:
        recommendations, msg_cost = draft_outreach_messages(recommendations, profile)
        total_api_cost += msg_cost

    # ── Step 12: Save all jobs to SQLite ──
    logger.info("Step 10: Saving job data to SQLite...")
    for job in scored_jobs:
        upsert_job(job)
    for job in new_jobs:
        if job not in scored_jobs:
            upsert_job(job)

    # ── Step 13: Export CSVs ──
    logger.info("Step 11: Exporting CSVs...")
    export_daily_csvs()
    if datetime.now().weekday() == 6:
        logger.info("Sunday — generating weekly report...")
        generate_weekly_report()

    # ── Step 14: Send email ──
    logger.info("Step 12: Sending email...")
    top_score = recommendations[0].ai_match_score if recommendations else 0
    summary = build_email_summary(recommendations, len(new_jobs), scraper_stats)
    csv_path = EXPORTS_DIR / "recommendations_today.csv"
    email_ok = send_report(csv_path, summary, len(recommendations), top_score)
    if email_ok:
        logger.info("EMAIL: sent successfully")
    else:
        logger.error("EMAIL: FAILED — check logs above for details")
        send_failure_alert("Daily report email failed to send. Pipeline data was saved to SQLite.")

    # ── Log run stats ──
    duration = time.time() - start_time
    log_run(
        total_scraped, len(new_jobs), len(filtered),
        len([j for j in recommendations if j.company_intro]),
        total_api_cost, "; ".join(errors), duration,
        jobs_recommended=len(recommendations),
        jobs_prefilter_passed=len(filtered),
    )

    logger.info(f"Pipeline completed in {duration:.1f}s | Cost: ${total_api_cost:.4f}")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception as e:
        logging.getLogger("pipeline").exception("Pipeline crashed")
        send_failure_alert(str(e))
        sys.exit(1)
