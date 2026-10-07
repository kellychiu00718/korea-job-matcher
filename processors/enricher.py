import json
import logging
import os
from typing import List, Tuple

from .models import Job

logger = logging.getLogger(__name__)


def enrich_jobs(jobs: List[Job], profile: dict,
                max_budget: float = 0.30) -> tuple[list[Job], float]:
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    tavily_key = os.getenv("TAVILY_API_KEY", "")

    if not api_key:
        logger.warning("No ANTHROPIC_API_KEY — skipping enrichment")
        return jobs, 0.0

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
    except ImportError:
        logger.warning("anthropic package not installed — skipping enrichment")
        return jobs, 0.0

    total_cost = 0.0
    skill_summary = profile.get("skill_summary_for_ai", "")

    for job in jobs:
        if job.ai_match_score < 70:
            continue

        company_context = _search_company(job.company, tavily_key)

        prompt = f"""你是一位資深職涯顧問與市場研究員。請根據以下資訊，為求職者提供這間公司和職缺的深度分析。

## 公司名稱: {job.company}
## 職缺: {job.title}
## JD 摘要: {(job.jd_text or job.title)[:1500]}
## 網路搜尋結果:
{company_context[:2000]}

## 求職者背景:
{skill_summary}

請回傳 JSON（不要 markdown code block）:
{{
  "company_intro": "<公司簡介，2-3句>",
  "products_services": "<主要產品與服務>",
  "business_model": "<商業模式與利潤來源>",
  "vision_goals": "<公司願景與目標>",
  "ideal_candidate": "<想要的人才特質，從JD萃取>",
  "market_position": "<市場定位與主要競爭對手>",
  "team_function": "<這個職位所在團隊負責的業務面向>",
  "positioning_advice": "<求職者應如何針對此職缺定位履歷，具體到該強調哪些經歷>"
}}"""

        try:
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.content[0].text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            result = _safe_json_parse(text)
            job.company_intro = result.get("company_intro", "")
            job.products_services = result.get("products_services", "")
            job.business_model = result.get("business_model", "")
            job.vision_goals = result.get("vision_goals", "")
            job.ideal_candidate = result.get("ideal_candidate", "")
            job.market_position = result.get("market_position", "")
            job.team_function = result.get("team_function", "")
            if result.get("positioning_advice"):
                job.positioning_advice = result["positioning_advice"]

            cost = (resp.usage.input_tokens * 0.80 + resp.usage.output_tokens * 4.0) / 1_000_000
            total_cost += cost

            if total_cost > max_budget:
                logger.warning(f"Enrichment budget ${max_budget} reached. Stopping enrichment.")
                break

        except Exception as e:
            logger.warning(f"Enrichment failed for {job.company} - {job.title}: {e}")

    logger.info(f"Enrichment cost: ${total_cost:.4f}")
    return jobs, total_cost


def _search_company(company_name: str, tavily_key: str) -> str:
    if not tavily_key:
        return ""

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=tavily_key)
        result = client.search(
            query=f"{company_name} company business model products Korea",
            max_results=3,
            search_depth="basic",
        )
        snippets = []
        for r in result.get("results", []):
            snippets.append(f"- {r.get('title', '')}: {r.get('content', '')[:300]}")
        return "\n".join(snippets)
    except Exception as e:
        logger.warning(f"Tavily search failed for {company_name}: {e}")
        return ""


def _safe_json_parse(text: str) -> dict:
    import re
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to fix truncated JSON by closing open strings and braces
    fixed = text.rstrip()
    if not fixed.endswith("}"):
        if fixed.count('"') % 2 == 1:
            fixed += '"'
        open_braces = fixed.count("{") - fixed.count("}")
        fixed += "}" * max(open_braces, 0)

    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Extract whatever key-value pairs we can with regex
    result = {}
    for key in ["company_intro", "products_services", "business_model",
                 "vision_goals", "ideal_candidate", "market_position",
                 "team_function", "positioning_advice"]:
        match = re.search(rf'"{key}"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
        if match:
            result[key] = match.group(1).replace('\\"', '"').replace("\\n", "\n")

    if result:
        return result
    raise json.JSONDecodeError("Could not parse", text, 0)
