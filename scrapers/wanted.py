import json
import logging
from typing import List

from .base import BaseScraper
from processors.models import Job

logger = logging.getLogger(__name__)

CATEGORY_MAP = {
    "sales": 530,
    "bd": 507,
    "consultant": 507,
    "marketing": 523,
    "data": 518,
    "design": 516,
}


class WantedScraper(BaseScraper):
    source_name = "wanted"
    API_URL = "https://www.wanted.co.kr/api/v4/jobs"
    DETAIL_URL = "https://www.wanted.co.kr/api/v4/jobs"

    def scrape(self, keywords: List[str], max_results: int = 50) -> List[Job]:
        all_jobs: List[Job] = []
        seen_ids = set()

        category_ids = set()
        for kw in keywords:
            kw_lower = kw.lower()
            for key, cat_id in CATEGORY_MAP.items():
                if key in kw_lower:
                    category_ids.add(cat_id)
        if not category_ids:
            category_ids = {530, 507, 523}

        for cat_id in category_ids:
            if len(all_jobs) >= max_results:
                break

            params = {
                "country": "kr",
                "job_sort": "job.latest_order",
                "years": 0,
                "locations": "all",
                "limit": 20,
                "offset": 0,
                "tag_type_id": cat_id,
            }

            try:
                resp = self._get(self.API_URL, params=params)
                data = resp.json()
            except Exception as e:
                logger.warning(f"[wanted] API failed for category {cat_id}: {e}")
                self._try_html_fallback(cat_id, all_jobs, seen_ids, max_results)
                continue

            job_list = data.get("data", [])
            if not job_list and isinstance(data, list):
                job_list = data

            for item in job_list:
                job_id = str(item.get("id", ""))
                if not job_id or job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                company_info = item.get("company", {})
                if isinstance(company_info, dict):
                    company_name = company_info.get("name", "")
                else:
                    company_name = str(company_info)

                job = Job(
                    source="wanted",
                    source_id=job_id,
                    url=f"https://www.wanted.co.kr/wd/{job_id}",
                    title=item.get("position", item.get("title", "")),
                    company=company_name,
                    location=item.get("address", {}).get("full_location", "") if isinstance(item.get("address"), dict) else "",
                )
                all_jobs.append(job)

        return all_jobs[:max_results]

    def _try_html_fallback(self, cat_id: int, all_jobs: List[Job],
                           seen_ids: set, max_results: int):
        try:
            from bs4 import BeautifulSoup

            url = f"https://www.wanted.co.kr/wdlist/{cat_id}?country=kr&job_sort=job.latest_order&years=0"
            resp = self._get(url)
            soup = BeautifulSoup(resp.text, "lxml")

            script_tags = soup.select("script")
            for script in script_tags:
                if script.string and "window.__NEXT_DATA__" in script.string:
                    import re
                    match = re.search(r'window\.__NEXT_DATA__\s*=\s*({.*?})\s*;?\s*$',
                                      script.string, re.DOTALL)
                    if match:
                        data = json.loads(match.group(1))
                        props = data.get("props", {}).get("pageProps", {})
                        jobs_data = props.get("jobs", [])
                        for item in jobs_data:
                            job_id = str(item.get("id", ""))
                            if not job_id or job_id in seen_ids:
                                continue
                            seen_ids.add(job_id)
                            job = Job(
                                source="wanted",
                                source_id=job_id,
                                url=f"https://www.wanted.co.kr/wd/{job_id}",
                                title=item.get("position", ""),
                                company=item.get("company", {}).get("name", ""),
                            )
                            all_jobs.append(job)
                            if len(all_jobs) >= max_results:
                                return
                    break

        except Exception as e:
            logger.warning(f"[wanted] HTML fallback also failed for category {cat_id}: {e}")
