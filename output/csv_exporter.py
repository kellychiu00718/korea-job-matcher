import csv
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "jobs.db"
EXPORTS_DIR = Path(__file__).resolve().parent.parent / "data" / "exports"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _sanitize(val) -> str:
    if val is None:
        return ""
    return str(val).replace("\n", " | ").replace("\r", "")


def _write_csv(filepath: Path, rows: list[sqlite3.Row], columns: list[str]):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        for row in rows:
            writer.writerow([_sanitize(row[col]) for col in columns])
    logger.info(f"CSV exported: {filepath.name} ({len(rows)} rows)")


def export_daily_csvs():
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    _export_jobs_current()
    _export_daily_stats()
    _export_recommendations_today()


def _export_jobs_current():
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM v_jobs_current").fetchall()
    conn.close()

    if not rows:
        logger.info("CSV: no jobs for jobs_current.csv")
        return

    columns = rows[0].keys()
    _write_csv(EXPORTS_DIR / "jobs_current.csv", rows, columns)


def _export_daily_stats():
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM v_daily_stats").fetchall()
    conn.close()

    if not rows:
        logger.info("CSV: no stats for daily_stats.csv")
        return

    columns = rows[0].keys()
    _write_csv(EXPORTS_DIR / "daily_stats.csv", rows, columns)


def _export_recommendations_today():
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM v_recommendations_today").fetchall()
    conn.close()

    if not rows:
        logger.info("CSV: no recommendations for today")
        return

    columns = rows[0].keys()
    _write_csv(EXPORTS_DIR / "recommendations_today.csv", rows, columns)
