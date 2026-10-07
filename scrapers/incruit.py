import re
import logging
from typing import List

from bs4 import BeautifulSoup

from .base import BaseScraper
from processors.models import Job

logger = logging.getLogger(__name__)


class IncruitScraper(BaseScraper):
    source_name = "incruit"
    SEARCH_URL = "https://search.incruit.com/list/search.asp"

    def scrape(self, keywords: List[str], max_results: int = 50) -> List[Job]:
        all_jobs: List[Job] = []
        seen_ids = set()

        for keyword in keywords:
            if len(all_jobs) >= max_results:
                break

            params = {
                "col": "job",
                "kw": keyword,
                "startno": 0,
            }

            try:
                resp = self._get(self.SEARCH_URL, params=params)
                resp.encoding = "utf-8"
                soup = BeautifulSoup(resp.text, "lxml")
            except Exception as e:
                logger.warning(f"[incruit] Failed for keyword '{keyword}': {e}")
                continue

            container = soup.select_one("div.cBbslist_contenst")
            if not container:
                continue

            items = container.select("li.c_col")

            for item in items:
                title_el = item.select_one("div.cell_mid a")
                if not title_el:
                    continue

                href = title_el.get("href", "")
                if not href:
                    continue

                job_id_match = re.search(r'job=(\d+)', href)
                if job_id_match:
                    job_id = job_id_match.group(1)
                else:
                    job_id = href

                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                title = title_el.get_text(strip=True)
                if not title:
                    continue

                company_el = item.select_one("div.cell_first a.cpname")
                company = company_el.get_text(strip=True) if company_el else ""

                exp_el = item.select_one("div.cell_mid span.cl_md")
                exp_text = ""
                if exp_el:
                    for span in item.select("div.cell_mid span.cl_md"):
                        t = span.get_text(strip=True)
                        if "경력" in t or "신입" in t:
                            exp_text = t
                            break

                date_el = item.select_one("div.cell_last")
                date_text = date_el.get_text(strip=True) if date_el else ""

                url = href if href.startswith("http") else f"https://job.incruit.com{href}"

                job = Job(
                    source="incruit",
                    source_id=str(job_id),
                    url=url,
                    title=title,
                    company=company,
                    experience_required=exp_text,
                    posted_date=date_text,
                )
                all_jobs.append(job)

        return all_jobs[:max_results]
