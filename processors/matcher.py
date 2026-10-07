import json
import logging
import os
from pathlib import Path
from typing import List, Tuple

import yaml

from .models import Job

logger = logging.getLogger(__name__)


def _clamp_score(raw: float) -> float:
    return max(0.0, min(100.0, raw))

SKILL_PROFILE_PATH = Path(__file__).resolve().parent.parent / "config" / "skill_profile.yaml"


def load_skill_profile() -> dict:
    with open(SKILL_PROFILE_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def keyword_score(job: Job, profile: dict) -> float:
    text = (job.title + " " + job.jd_text + " " + job.company).lower()

    score = 0.0
    for kw in profile.get("high_match_keywords", []):
        if kw.lower() in text:
            score += 3.0

    for kw in profile.get("medium_match_keywords", []):
        if kw.lower() in text:
            score += 2.0

    for kw in profile.get("negative_keywords", []):
        if kw.lower() in text:
            score -= 5.0

    return max(score, 0.0)


def keyword_prefilter(jobs: List[Job], profile: dict, min_score: float = 2.0) -> List[Job]:
    scored = []
    for job in jobs:
        ks = keyword_score(job, profile)
        job.keyword_score = ks
        if ks >= min_score:
            job.prefilter_passed = 1
            scored.append(job)

    scored.sort(key=lambda j: j.keyword_score, reverse=True)
    return scored


def apply_age_cutoff(jobs: List[Job], max_days: int = 30) -> List[Job]:
    kept = []
    for job in jobs:
        days = job.effective_freshness_days
        if days is None or days <= max_days:
            kept.append(job)
    return kept


def ai_match_and_score(jobs: List[Job], profile: dict,
                       max_daily_budget: float = 0.50) -> List[Job]:
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.warning("No ANTHROPIC_API_KEY — skipping AI matching, using keyword scores only")
        for job in jobs:
            job.ai_match_score = _clamp_score(job.keyword_score * 5)
        return jobs

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
    except ImportError:
        logger.warning("anthropic package not installed — using keyword scores only")
        for job in jobs:
            job.ai_match_score = _clamp_score(job.keyword_score * 5)
        return jobs

    skill_summary = profile.get("skill_summary_for_ai", "")
    model = "claude-haiku-4-5-20251001"
    estimated_cost = 0.0

    for job in jobs:
        jd_preview = (job.jd_text or job.title)[:2000]

        prompt = f"""你是一位職涯顧問。請根據 JD 的實際工作內容（非職稱）來評估此職缺與求職者的匹配程度。

## 評分原則（嚴格遵守）
1. **以 JD 內容為主**：忽略職稱，專注分析 JD 描述的日常工作、所需技能、職責範圍是否匹配求職者的能力
2. **經歷要求**：求職者是應屆畢業生。經歷要求 0-2 年加分（+10），3-5 年可接受（+0），超過 5 年直接扣 30 分
3. **公司類型**：不要因公司類型加分或扣分，公司類型僅供參考，不影響匹配分數
4. **不要因為職稱看起來不相關就給低分** — 很多職缺的實際工作內容可能與職稱有落差，以 JD 內容為準

## 求職者背景
{skill_summary}

## 職缺資訊
- 職稱: {job.title}
- 公司: {job.company}（類型: {job.company_type}）
- 經歷要求: {job.experience_required}
- JD 內容:
{jd_preview}

## 請回傳 JSON（不要 markdown code block）:
{{
  "score": <0-100 整數>,
  "reasons": "<2-3 句說明為什麼匹配或不匹配，著重 JD 工作內容與求職者能力的對應>",
  "positioning": "<1-2 句建議求職者如何針對此職缺定位自己的履歷>"
}}"""

        try:
            resp = client.messages.create(
                model=model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            result = json.loads(text)
            job.ai_match_score = _clamp_score(float(result.get("score", 0)))
            job.match_reasons = result.get("reasons", "")
            job.positioning_advice = result.get("positioning", "")

            input_tokens = resp.usage.input_tokens
            output_tokens = resp.usage.output_tokens
            cost = (input_tokens * 0.80 + output_tokens * 4.0) / 1_000_000
            estimated_cost += cost

            if estimated_cost > max_daily_budget:
                logger.warning(f"Daily AI budget ${max_daily_budget} reached (${estimated_cost:.3f}). Remaining jobs use keyword scores.")
                break

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse AI response for {job.title}: {e}")
            job.ai_match_score = _clamp_score(job.keyword_score * 5)
        except Exception as e:
            logger.warning(f"AI scoring failed for {job.title}: {e}")
            job.ai_match_score = _clamp_score(job.keyword_score * 5)

    for job in jobs:
        if job.ai_match_score == 0 and job.keyword_score > 0:
            job.ai_match_score = _clamp_score(job.keyword_score * 5)

    jobs.sort(key=lambda j: j.ai_match_score, reverse=True)
    logger.info(f"AI matching cost: ${estimated_cost:.4f}")
    return jobs, estimated_cost


FRESHNESS_BONUS = [
    (3, 10),
    (7, 8),
    (14, 5),
    (30, 2),
]

COMPANY_TYPE_BONUS = {
    "외국계": 6,
    "대기업": 4,
    "스타트업": 2,
    "일반": 0,
    "불확인": 0,
}


def _freshness_bonus(job: Job) -> float:
    days = job.effective_freshness_days
    if days is None:
        return 0.0
    for threshold, bonus in FRESHNESS_BONUS:
        if days <= threshold:
            return bonus
    return 0.0


def _ranking_score(job: Job) -> float:
    base = job.ai_match_score

    if getattr(job, 'company_type_confidence', 'unverified') != 'unverified':
        base += COMPANY_TYPE_BONUS.get(job.company_type, 0)

    base += _freshness_bonus(job)
    return base


def select_top_recommendations(jobs: List[Job], max_count: int = 10) -> List[Job]:
    qualified = [j for j in jobs if j.ai_match_score >= 40]
    for j in qualified:
        j.ranking_score = _ranking_score(j)
    ranked = sorted(qualified, key=lambda j: j.ranking_score, reverse=True)
    return ranked[:max_count]
