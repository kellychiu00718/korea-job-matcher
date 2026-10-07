import re
import logging
from typing import List

from bs4 import BeautifulSoup

from .base import BaseScraper
from processors.models import Job

logger = logging.getLogger(__name__)


class JobKoreaScraper(BaseScraper):
    source_name = "jobkorea"
    SEARCH_URL = "https://www.jobkorea.co.kr/Search/"

    def scrape(self, keywords: List[str], max_results: int = 50) -> List[Job]:
        all_jobs: List[Job] = []
        seen_ids = set()

        for keyword in keywords:
            if len(all_jobs) >= max_results:
                break

            params = {
                "stext": keyword,
                "tabType": "recruit",
                "Page_No": 1,
            }

            try:
                resp = self._get(self.SEARCH_URL, params=params)
                resp.encoding = "utf-8"
            except Exception as e:
                logger.warning(f"[jobkorea] Failed for keyword '{keyword}': {e}")
                continue

            soup = BeautifulSoup(resp.text, "lxml")
            cards = soup.select("div[class*='shadow-list']")

            for card in cards:
                gi_links = card.select("a[href*='GI_Read']")
                if not gi_links:
                    continue

                title = ""
                company = ""
                job_id = ""
                href = ""

                for link in gi_links:
                    text = link.get_text(strip=True)
                    link_href = link.get("href", "")

                    if not job_id:
                        match = re.search(r"GI_Read/(\d+)", link_href)
                        if match:
                            job_id = match.group(1)
                            href = link_href

                    if len(text) > 5 and not title:
                        title = text
                    elif len(text) > 1 and title and not company:
                        company = text

                if not job_id or not title:
                    continue
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                exp = ""
                location = ""
                for span in card.select("span"):
                    t = span.get_text(strip=True)
                    if ("경력" in t or "신입" in t) and not exp:
                        exp = t
                    if any(kw in t for kw in ["서울", "경기", "부산", "대구", "인천", "전국", "대전", "광주", "울산", "세종"]) and not location:
                        location = t

                url = href
                if not url.startswith("http"):
                    url = f"https://www.jobkorea.co.kr{href}"

                job = Job(
                    source="jobkorea",
                    source_id=str(job_id),
                    url=url,
                    title=title,
                    company=company,
                    location=location,
                    experience_required=exp,
                )
                all_jobs.append(job)

        return all_jobs[:max_results]
