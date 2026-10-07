import logging
from datetime import datetime
from typing import List

from processors.models import Job

logger = logging.getLogger(__name__)


def build_email_summary(recommendations: List[Job], total_new: int,
                        scraper_stats: dict) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"Daily Job Shortlist — {today}",
        f"新增職缺: {total_new} 筆 | 推薦: {len(recommendations)} 筆",
        "",
    ]

    if scraper_stats:
        lines.append("平台統計:")
        for source, count in scraper_stats.items():
            status = "⚠️ 0筆" if count == 0 else ""
            lines.append(f"  {source}: {count} 筆 {status}")
        lines.append("")

    lines.append("=" * 50)
    lines.append("今日推薦 TOP 職缺:")
    lines.append("=" * 50)

    for i, job in enumerate(recommendations[:10], 1):
        lines.extend([
            f"\n#{i} [{job.ai_match_score:.0f}分] {job.title}",
            f"   公司: {job.company} ({job.company_type})" if job.company_type else f"   公司: {job.company}",
            f"   來源: {job.source} | {job.freshness_label}",
            f"   匹配: {job.match_reasons[:80]}..." if len(job.match_reasons) > 80 else f"   匹配: {job.match_reasons}",
            f"   連結: {job.url}",
        ])

    lines.extend([
        "",
        "詳細資訊請見附件 CSV 或 Tableau 儀表板。",
        "— Korea Job Matcher",
    ])

    return "\n".join(lines)
