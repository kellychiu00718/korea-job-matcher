import os
import logging
from datetime import datetime, timedelta
from typing import List

from .base import BaseScraper
from processors.models import Job

logger = logging.getLogger(__name__)


class SaraminScraper(BaseScraper):
    source_name = "saramin"
    BASE_URL = "https://oapi.saramin.co.kr/job-search"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_key = os.getenv("SARAMIN_API_KEY", "")

    def scrape(self, keywords: List[str], max_results: int = 50) -> List[Job]:
        if not self.api_key:
            logger.warning("[saramin] No API key set — skipping. Register at oapi.saramin.co.kr")
            return []

        all_jobs: List[Job] = []
        seen_ids = set()
        published_min = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        for keyword in keywords:
            if len(all_jobs) >= max_results:
                break

            params = {
                "access-key": self.api_key,
                "keywords": keyword,
                "loc_cd": "117000",
                "sort": "pd",
                "count": min(50, max_results - len(all_jobs)),
                "published_min": published_min,
            }

            try:
                resp = self._get(self.BASE_URL, params=params)
                data = resp.json()
            except Exception as e:
                logger.warning(f"[saramin] Failed for keyword '{keyword}': {e}")
                continue

            jobs_data = data.get("jobs", {}).get("job", [])
            if isinstance(jobs_data, dict):
                jobs_data = [jobs_data]

            for item in jobs_data:
                job_id = str(item.get("id", ""))
                if not job_id or job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                position = item.get("position", {})
                company = item.get("company", {}).get("detail", {})
                salary = item.get("salary", {})

                exp_min = position.get("experience-level", {}).get("min", 0)
                if isinstance(exp_min, (int, float)) and exp_min > 5:
                    continue

                job = Job(
                    source="saramin",
                    source_id=job_id,
                    url=item.get("url", ""),
                    title=position.get("title", ""),
                    company=company.get("name", item.get("company", {}).get("detail", {}).get("name", "")),
                    location=position.get("location", {}).get("name", ""),
                    experience_required=position.get("experience-level", {}).get("name", ""),
                    salary_info=salary.get("name", ""),
                    posted_date=item.get("posting-timestamp", ""),
                    deadline=item.get("expiration-timestamp", ""),
                )

                if job.posted_date and job.posted_date.isdigit():
                    try:
                        job.posted_date = datetime.fromtimestamp(int(job.posted_date)).isoformat()
                    except (ValueError, OSError):
                        pass
                if job.deadline and job.deadline.isdigit():
                    try:
                        job.deadline = datetime.fromtimestamp(int(job.deadline)).isoformat()
                    except (ValueError, OSError):
                        pass

                all_jobs.append(job)

        return all_jobs[:max_results]
