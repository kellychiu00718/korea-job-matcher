import json
import logging
import os
from pathlib import Path
from typing import List
from urllib.parse import quote

import yaml

from .models import Job

logger = logging.getLogger(__name__)

_PROFILE_PATH = Path(__file__).resolve().parent.parent / "config" / "skill_profile.yaml"


def _load_user_name() -> tuple[str, str]:
    try:
        with open(_PROFILE_PATH, encoding="utf-8") as f:
            profile = yaml.safe_load(f)
        summary = profile.get("skill_summary_for_ai", "")
        first_line = summary.strip().split("\n")[0]
        name = first_line.split("—")[0].strip() if "—" in first_line else ""
        if name:
            return name, name.split("(")[-1].rstrip(")") if "(" in name else name
    except Exception:
        pass
    return "", ""


def generate_search_url(company: str, department: str = "") -> str:
    query = company
    if department:
        query += f" {department}"
    return f"https://www.linkedin.com/search/results/people/?keywords={quote(query)}&origin=GLOBAL_SEARCH_HEADER"


def add_linkedin_info(jobs: List[Job]) -> List[Job]:
    for job in jobs:
        if job.ai_match_score < 70:
            continue
        dept_hint = job.team_function or job.title
        job.linkedin_search_url = generate_search_url(job.company, dept_hint)
    return jobs


def draft_outreach_messages(jobs: List[Job], profile: dict) -> tuple[list[Job], float]:
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        for job in jobs:
            if job.ai_match_score >= 70:
                job.connect_message_draft = _template_connect(job)
                job.coffee_chat_draft = _template_coffee_chat(job)
        return jobs, 0.0

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
    except ImportError:
        for job in jobs:
            if job.ai_match_score >= 70:
                job.connect_message_draft = _template_connect(job)
                job.coffee_chat_draft = _template_coffee_chat(job)
        return jobs, 0.0

    skill_summary = profile.get("skill_summary_for_ai", "")
    total_cost = 0.0

    for job in jobs:
        if job.ai_match_score < 70:
            continue

        prompt = f"""請為以下職缺擬定兩份 LinkedIn 訊息。

## 職缺: {job.title} @ {job.company}
## 團隊/部門: {job.team_function or 'N/A'}
## 求職者背景摘要: {skill_summary[:500]}

請回傳 JSON（不要 markdown code block）:
{{
  "connect_message": "<韓文 LinkedIn Connect 訊息，300字符以內，簡短自我介紹+為什麼對這個職位/團隊有興趣+希望交流>",
  "coffee_chat_email": "<韓文 coffee chat 邀約信，包含：自我介紹、對公司/職位的理解、想請教的具體問題、時間提議。約 200 字>"
}}"""

        try:
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            result = json.loads(text)
            job.connect_message_draft = result.get("connect_message", _template_connect(job))
            job.coffee_chat_draft = result.get("coffee_chat_email", _template_coffee_chat(job))

            cost = (resp.usage.input_tokens * 0.80 + resp.usage.output_tokens * 4.0) / 1_000_000
            total_cost += cost

        except Exception as e:
            logger.warning(f"Message drafting failed for {job.company}: {e}")
            job.connect_message_draft = _template_connect(job)
            job.coffee_chat_draft = _template_coffee_chat(job)

    logger.info(f"Message drafting cost: ${total_cost:.4f}")
    return jobs, total_cost


def _template_connect(job: Job) -> str:
    full_name, short_name = _load_user_name()
    display = full_name or "지원자"
    return (
        f"안녕하세요, {display}입니다. "
        f"{job.company}의 {job.title} 포지션에 관심이 있어 연락드립니다. "
        f"혹시 잠시 이야기를 나눌 수 있을까요?"
    )


def _template_coffee_chat(job: Job) -> str:
    full_name, short_name = _load_user_name()
    display = full_name or "지원자"
    sign_off = short_name or display
    return (
        f"안녕하세요,\n\n"
        f"{display}이라고 합니다. "
        f"현재 {job.company}의 {job.title} 포지션에 지원을 고려하고 있습니다.\n\n"
        f"이 팀에서의 업무 경험과 팀 문화에 대해 여쭤볼 수 있을까요? "
        f"편하신 시간에 20분 정도 커피챗이 가능하시다면 감사하겠습니다.\n\n"
        f"감사합니다,\n{sign_off}"
    )
