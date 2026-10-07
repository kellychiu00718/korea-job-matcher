import time
import random
import logging
from abc import ABC, abstractmethod
from typing import List

import requests

from processors.models import Job

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
]


class BaseScraper(ABC):
    source_name: str = "unknown"

    def __init__(self, delay: float = 2.5, max_retries: int = 3):
        self.delay = delay
        self.max_retries = max_retries
        self.session = requests.Session()
        self._rotate_ua()

    def _rotate_ua(self):
        self.session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        })

    def _get(self, url: str, params: dict = None, **kwargs) -> requests.Response:
        for attempt in range(1, self.max_retries + 1):
            try:
                self._rotate_ua()
                time.sleep(self.delay + random.uniform(0, 1))
                resp = self.session.get(url, params=params, timeout=15, **kwargs)
                if resp.status_code == 429:
                    wait = min(60, self.delay * (2 ** attempt))
                    logger.warning(f"[{self.source_name}] 429 rate limited, waiting {wait:.0f}s")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp
            except requests.RequestException as e:
                logger.warning(f"[{self.source_name}] Request failed (attempt {attempt}): {e}")
                if attempt == self.max_retries:
                    raise
                time.sleep(self.delay * attempt)
        raise RuntimeError(f"[{self.source_name}] All retries exhausted for {url}")

    @abstractmethod
    def scrape(self, keywords: List[str], max_results: int = 50) -> List[Job]:
        ...

    def scrape_safe(self, keywords: List[str], max_results: int = 50) -> List[Job]:
        try:
            jobs = self.scrape(keywords, max_results)
            logger.info(f"[{self.source_name}] Scraped {len(jobs)} jobs")
            if len(jobs) == 0:
                logger.warning(f"[{self.source_name}] Zero results — site may have changed")
            return jobs
        except Exception as e:
            logger.error(f"[{self.source_name}] Scraper failed: {e}")
            return []
