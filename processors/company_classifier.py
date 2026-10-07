import logging
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List

from .models import Job

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "jobs.db"

FOREIGN_SIGNALS = [
    "외국계", "글로벌", "global", "multinational", "inc.", "corp.",
    "gmbh", "ltd", "s.a.", "headquarters",
]

STARTUP_SIGNALS = ["스타트업", "startup", "시리즈", "series a", "series b"]

CONGLOMERATE_SIGNALS = [
    "그룹", "삼성", "samsung", "현대", "hyundai", "lg",
    "sk", "sk하이닉스", "hynix", "롯데", "포스코", "cj",
    "한화", "네이버", "naver", "라인", "line corp",
    "카카오", "kakao", "쿠팡", "coupang", "배달의민족", "우아한형제들",
    "토스", "비바리퍼블리카", "당근", "크래프톤", "krafton",
    "넥슨", "nexon", "엔씨소프트", "ncsoft", "넷마블", "netmarble",
    "두나무", "하이브", "hybe",
]

FOREIGN_VERIFY_KEYWORDS = [
    "외국계", "글로벌 기업", "global company", "multinational",
    "본사", "headquarters", "foreign", "해외 본사",
]
CONGLOMERATE_VERIFY_KEYWORDS = [
    "대기업", "대형", "그룹", "재벌", "conglomerate",
    "상장", "코스피", "kospi", "fortune 500",
]
STARTUP_VERIFY_KEYWORDS = [
    "스타트업", "startup", "시리즈", "series", "투자",
    "funding", "벤처", "venture",
]


def _normalize_company_name(name: str) -> str:
    name = name.lower().strip()
    for suffix in ["(주)", "㈜", "주식회사", "inc.", "inc", "corp.", "corp",
                    "ltd.", "ltd", "co.", "co", "llc", "gmbh"]:
        name = name.replace(suffix, "")
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _pattern_match(text: str) -> str:
    text = text.lower()
    for s in FOREIGN_SIGNALS:
        if s in text:
            return "외국계"
    for s in STARTUP_SIGNALS:
        if s in text:
            return "스타트업"
    for s in CONGLOMERATE_SIGNALS:
        if s in text:
            return "대기업"
    return "일반"


class CompanyClassifier:
    def __init__(self, tavily_key: str = "", max_daily_searches: int = 20):
        self._tavily_key = tavily_key
        self._max_daily = max_daily_searches
        self._daily_count = 0
        self._cache: dict[str, tuple[str, str, str]] = {}
        self._load_cache()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn

    def _load_cache(self):
        try:
            conn = self._get_conn()
            rows = conn.execute(
                "SELECT normalized_name, company_type, confidence, source FROM company_cache"
            ).fetchall()
            conn.close()
            for row in rows:
                self._cache[row["normalized_name"]] = (
                    row["company_type"], row["confidence"], row["source"]
                )
            logger.info(f"Company cache loaded: {len(self._cache)} entries")
        except sqlite3.OperationalError:
            pass

    def _save_to_cache(self, normalized: str, company_type: str,
                       confidence: str, source: str, snippet: str = ""):
        self._cache[normalized] = (company_type, confidence, source)
        try:
            conn = self._get_conn()
            conn.execute(
                """INSERT OR REPLACE INTO company_cache
                   (normalized_name, company_type, confidence, source, verified_at, raw_search_snippet)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (normalized, company_type, confidence, source,
                 datetime.now().isoformat(), snippet[:500]),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to save company cache: {e}")

    def _tavily_verify(self, company_name: str, pattern_type: str) -> tuple[str, str]:
        if not self._tavily_key or self._daily_count >= self._max_daily:
            return pattern_type, "pattern_match"

        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=self._tavily_key)
            result = client.search(
                query=f"{company_name} 회사 기업 정보",
                max_results=3,
                search_depth="basic",
            )
            self._daily_count += 1

            snippets = []
            for r in result.get("results", []):
                snippets.append(r.get("content", "")[:300])
            combined = " ".join(snippets).lower()

            if pattern_type == "외국계":
                verify_kws = FOREIGN_VERIFY_KEYWORDS
            elif pattern_type == "대기업":
                verify_kws = CONGLOMERATE_VERIFY_KEYWORDS
            elif pattern_type == "스타트업":
                verify_kws = STARTUP_VERIFY_KEYWORDS
            else:
                return pattern_type, "pattern_match"

            confirmed = any(kw in combined for kw in verify_kws)
            if confirmed:
                return pattern_type, "verified"

            return "불확인", "unverified"

        except Exception as e:
            logger.warning(f"Tavily verify failed for {company_name}: {e}")
            return pattern_type, "pattern_match"

    def classify(self, job: Job) -> None:
        normalized = _normalize_company_name(job.company)

        if normalized in self._cache:
            ctype, confidence, source = self._cache[normalized]
            job.company_type = ctype
            job.company_type_confidence = confidence
            job.company_type_source = source
            return

        text = (job.jd_text + " " + job.company)
        pattern_type = _pattern_match(text)

        if pattern_type != "일반":
            verified_type, confidence = self._tavily_verify(job.company, pattern_type)
            job.company_type = verified_type
            job.company_type_confidence = confidence
            job.company_type_source = "tavily" if confidence == "verified" else "pattern"
            snippet = f"pattern={pattern_type}, verified={confidence}"
        else:
            job.company_type = "불확인"
            job.company_type_confidence = "unverified"
            job.company_type_source = "default"
            snippet = "no pattern match"

        self._save_to_cache(normalized, job.company_type,
                            job.company_type_confidence,
                            job.company_type_source, snippet)

    def classify_batch(self, jobs: List[Job]) -> None:
        for job in jobs:
            self.classify(job)
        verified = sum(1 for j in jobs if j.company_type_confidence == "verified")
        pattern = sum(1 for j in jobs if j.company_type_confidence == "pattern_match")
        unverified = sum(1 for j in jobs if j.company_type_confidence == "unverified")
        logger.info(
            f"Company classification: {verified} verified, {pattern} pattern, "
            f"{unverified} unverified (Tavily calls: {self._daily_count})"
        )
