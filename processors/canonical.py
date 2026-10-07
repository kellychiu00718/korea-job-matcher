import logging
import re
from collections import defaultdict
from typing import List

from .models import Job

logger = logging.getLogger(__name__)

_LEGAL_SUFFIXES = [
    "(주)", "㈜", "주식회사", "inc.", "inc", "corp.", "corp",
    "ltd.", "ltd", "co.", "co,", "co", "llc", "gmbh", "s.a.",
    "株式会社", "有限公司",
]

_BRACKET_PATTERN = re.compile(r"[\[\(（【].*?[\]\)）】]")
_WHITESPACE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    text = text.lower().strip()
    for suffix in _LEGAL_SUFFIXES:
        text = text.replace(suffix, "")
    text = _BRACKET_PATTERN.sub("", text)
    text = _WHITESPACE.sub(" ", text).strip()
    return text


def canonical_key(company: str, title: str) -> str:
    nc = _normalize(company)
    nt = _normalize(title)
    if not nc or not nt:
        return ""
    return f"{nc}|{nt}"


def merge_cross_platform(jobs: List[Job]) -> List[Job]:
    for job in jobs:
        job.canonical_key = canonical_key(job.company, job.title)

    groups: dict[str, list[Job]] = defaultdict(list)
    no_key: list[Job] = []

    for job in jobs:
        if job.canonical_key:
            groups[job.canonical_key].append(job)
        else:
            no_key.append(job)

    merged: list[Job] = list(no_key)
    duplicates_found = 0

    for key, group in groups.items():
        if len(group) == 1:
            merged.append(group[0])
            continue

        duplicates_found += len(group) - 1
        group.sort(key=_completeness_score, reverse=True)
        winner = group[0]

        other_sources = [j.source for j in group[1:] if j.source != winner.source]
        if other_sources:
            winner.canonical_group_id = f"{winner.dedup_key}+{'+'.join(other_sources)}"

        merged.append(winner)

    if duplicates_found > 0:
        logger.info(f"Cross-platform dedup: merged {duplicates_found} duplicates from {len(jobs)} jobs -> {len(merged)}")
    return merged


def _completeness_score(job: Job) -> int:
    score = 0
    if job.jd_text:
        score += 10
    if job.posted_date:
        score += 5
    if job.salary_info:
        score += 3
    if job.experience_required:
        score += 2
    if job.location:
        score += 1
    return score
