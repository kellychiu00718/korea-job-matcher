import csv
import logging
import re
import sqlite3
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "jobs.db"
EXPORTS_DIR = Path(__file__).resolve().parent.parent / "data" / "exports" / "weekly"
SKILL_PROFILE_PATH = Path(__file__).resolve().parent.parent / "config" / "skill_profile.yaml"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _sanitize(val) -> str:
    if val is None:
        return ""
    return str(val).replace("\n", " | ").replace("\r", "")


def _write_csv(filepath: Path, headers: list[str], rows: list[list]):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for row in rows:
            writer.writerow([_sanitize(v) for v in row])
    logger.info(f"Weekly CSV: {filepath.name} ({len(rows)} rows)")


class WeeklyReportGenerator:
    def __init__(self):
        self.conn = _get_conn()
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    def generate_all(self):
        logger.info("Generating weekly report CSVs...")
        self._health()
        self._category_match()
        self._company_type()
        self._skills()
        self._source_quality()
        self._trends()
        self._experience()
        self.conn.close()
        logger.info("Weekly report complete")

    def _health(self):
        rows = self.conn.execute("SELECT * FROM v_weekly_health").fetchall()
        if not rows:
            return
        headers = rows[0].keys()
        data = [[row[h] for h in headers] for row in rows]
        _write_csv(EXPORTS_DIR / "weekly_health.csv", list(headers), data)

    def _category_match(self):
        from processors.role_classifier import classify_role

        rows = self.conn.execute("""
            SELECT title, ai_match_score
            FROM seen_jobs
            WHERE first_seen >= date('now', '-7 days')
              AND ai_match_score > 0
        """).fetchall()

        families: dict[str, list[float]] = {}
        for row in rows:
            family = classify_role(row["title"])
            families.setdefault(family, []).append(row["ai_match_score"])

        headers = ["role_family", "job_count", "avg_ai_score", "pct_above_40", "pct_above_70"]
        data = []
        for family, scores in sorted(families.items(), key=lambda x: -len(x[1])):
            count = len(scores)
            avg = round(sum(scores) / count, 1) if count else 0
            pct40 = round(100 * sum(1 for s in scores if s >= 40) / count, 1) if count else 0
            pct70 = round(100 * sum(1 for s in scores if s >= 70) / count, 1) if count else 0
            data.append([family, count, avg, pct40, pct70])

        _write_csv(EXPORTS_DIR / "weekly_category_match.csv", headers, data)

    def _company_type(self):
        rows = self.conn.execute("SELECT * FROM v_weekly_company_type").fetchall()
        if not rows:
            return
        headers = rows[0].keys()
        data = [[row[h] for h in headers] for row in rows]
        _write_csv(EXPORTS_DIR / "weekly_company_type.csv", list(headers), data)

    def _skills(self):
        try:
            with open(SKILL_PROFILE_PATH, encoding="utf-8") as f:
                profile = yaml.safe_load(f)
        except Exception:
            return

        all_keywords = (
            profile.get("high_match_keywords", []) +
            profile.get("medium_match_keywords", [])
        )

        rows = self.conn.execute("""
            SELECT match_reasons, ai_match_score
            FROM seen_jobs
            WHERE first_seen >= date('now', '-7 days')
              AND match_reasons != ''
              AND ai_match_score >= 40
        """).fetchall()

        skill_stats: dict[str, list[float]] = {}
        for row in rows:
            text = row["match_reasons"].lower()
            for kw in all_keywords:
                if kw.lower() in text:
                    skill_stats.setdefault(kw, []).append(row["ai_match_score"])

        headers = ["skill", "mention_count", "avg_score_when_mentioned"]
        data = []
        for skill, scores in sorted(skill_stats.items(), key=lambda x: -len(x[1])):
            data.append([
                skill,
                len(scores),
                round(sum(scores) / len(scores), 1),
            ])

        _write_csv(EXPORTS_DIR / "weekly_skills.csv", headers, data)

    def _source_quality(self):
        rows = self.conn.execute("SELECT * FROM v_weekly_source").fetchall()
        if not rows:
            return
        headers = rows[0].keys()
        data = [[row[h] for h in headers] for row in rows]
        _write_csv(EXPORTS_DIR / "weekly_source_quality.csv", list(headers), data)

    def _trends(self):
        rows = self.conn.execute("SELECT * FROM v_weekly_trends").fetchall()
        if not rows:
            return
        headers = rows[0].keys()
        data = [[row[h] for h in headers] for row in rows]
        _write_csv(EXPORTS_DIR / "weekly_trends.csv", list(headers), data)

    def _experience(self):
        rows = self.conn.execute("""
            SELECT experience_required, ai_match_score
            FROM seen_jobs
            WHERE first_seen >= date('now', '-7 days')
              AND experience_required != ''
        """).fetchall()

        categories = {
            "신입/0-2년": [],
            "3-5년": [],
            "6년+": [],
            "기타": [],
        }

        for row in rows:
            exp = row["experience_required"].lower()
            score = row["ai_match_score"]

            if any(k in exp for k in ["신입", "인턴", "0년", "1년", "2년", "0~", "1~2", "0-2"]):
                categories["신입/0-2년"].append(score)
            elif any(k in exp for k in ["3년", "4년", "5년", "3~", "3-5", "2~5"]):
                categories["3-5년"].append(score)
            elif any(k in exp for k in ["6년", "7년", "8년", "9년", "10년", "6~", "5년 이상", "경력"]):
                categories["6년+"].append(score)
            else:
                categories["기타"].append(score)

        total = sum(len(v) for v in categories.values())
        headers = ["experience_range", "job_count", "pct_of_total", "avg_ai_score"]
        data = []
        for cat, scores in categories.items():
            if not scores:
                continue
            data.append([
                cat,
                len(scores),
                round(100 * len(scores) / total, 1) if total else 0,
                round(sum(scores) / len(scores), 1),
            ])

        _write_csv(EXPORTS_DIR / "weekly_experience.csv", headers, data)


def generate_weekly_report():
    WeeklyReportGenerator().generate_all()
