from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class Job:
    source: str
    source_id: str
    url: str
    title: str
    company: str
    location: str = ""
    experience_required: str = ""
    salary_info: str = ""
    posted_date: str = ""
    deadline: str = ""
    jd_text: str = ""
    jd_language: str = ""
    company_type: str = ""
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Filled by matcher
    keyword_score: float = 0.0
    ai_match_score: float = 0.0
    match_reasons: str = ""
    positioning_advice: str = ""

    # Filled by enricher (only for high-score jobs)
    company_intro: str = ""
    products_services: str = ""
    business_model: str = ""
    vision_goals: str = ""
    ideal_candidate: str = ""
    market_position: str = ""
    team_function: str = ""

    # LinkedIn helper
    linkedin_search_url: str = ""
    connect_message_draft: str = ""
    coffee_chat_draft: str = ""

    # User tracking
    application_status: str = ""
    notes: str = ""

    # Company classification
    company_type_confidence: str = "unverified"
    company_type_source: str = ""

    # Cross-platform dedup
    canonical_key: str = ""
    canonical_group_id: str = ""

    # Computed fields
    effective_date: str = ""
    ranking_score: float = 0.0
    prefilter_passed: int = 0

    @property
    def dedup_key(self) -> str:
        return f"{self.source}:{self.source_id}"

    @property
    def freshness_days(self) -> Optional[int]:
        if not self.posted_date:
            return None
        try:
            posted = datetime.fromisoformat(self.posted_date)
            return (datetime.now() - posted).days
        except (ValueError, TypeError):
            return None

    @property
    def effective_freshness_days(self) -> Optional[int]:
        for date_str in (self.posted_date, self.scraped_at):
            if not date_str:
                continue
            try:
                dt = datetime.fromisoformat(date_str)
                return (datetime.now() - dt).days
            except (ValueError, TypeError):
                continue
        return None

    @property
    def freshness_label(self) -> str:
        days = self.effective_freshness_days
        if days is None:
            return "unknown"
        if days <= 3:
            return "\U0001f534 0-3d"
        if days <= 7:
            return "\U0001f7e0 4-7d"
        if days <= 14:
            return "\U0001f7e1 8-14d"
        if days <= 30:
            return "⚪ 15-30d"
        return "⚫ >30d"

    def detect_jd_language(self) -> str:
        if not self.jd_text:
            return "unknown"
        korean_chars = sum(1 for c in self.jd_text if '가' <= c <= '힣')
        total = len(self.jd_text)
        if total == 0:
            return "unknown"
        ratio = korean_chars / total
        if ratio > 0.3:
            return "Korean"
        return "English"

    def detect_company_type(self) -> str:
        text = (self.jd_text + " " + self.company).lower()
        foreign_signals = [
            "외국계", "글로벌", "global", "multinational", "inc.", "corp.",
            "gmbh", "ltd", "s.a.", "headquarters",
        ]
        startup_signals = ["스타트업", "startup", "시리즈", "series a", "series b"]
        conglomerate_signals = [
            "그룹", "삼성", "samsung", "현대", "hyundai", "lg",
            "sk", "sk하이닉스", "hynix", "롯데", "포스코", "cj",
            "한화", "네이버", "naver", "라인", "line corp",
            "카카오", "kakao", "쿠팡", "coupang", "배달의민족", "우아한형제들",
            "토스", "비바리퍼블리카", "당근", "크래프톤", "krafton",
            "넥슨", "nexon", "엔씨소프트", "ncsoft", "넷마블", "netmarble",
            "두나무", "하이브", "hybe",
        ]

        for s in foreign_signals:
            if s in text:
                return "외국계"
        for s in startup_signals:
            if s in text:
                return "스타트업"
        for s in conglomerate_signals:
            if s in text:
                return "대기업"
        return "일반"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["freshness_label"] = self.freshness_label
        return d
