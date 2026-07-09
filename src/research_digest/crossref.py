from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from html import unescape
import json
import os
import re
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import Journal


CROSSREF_API = "https://api.crossref.org/works"


@dataclass(frozen=True)
class Paper:
    id: str
    title: str
    authors: tuple[str, ...]
    summary: str
    summary_zh: str
    published: date
    link: str
    image_url: str
    source_urls: tuple[str, ...]
    journal: str
    impact_factor: float
    matched_keywords: tuple[str, ...]


def fetch_all(
    keywords: tuple[str, ...],
    journals: tuple[Journal, ...],
    days_back: int,
    max_items: int,
    minimum_impact_factor: float,
) -> list[Paper]:
    eligible = {
        _normalize(journal.name): journal
        for journal in journals
        if journal.impact_factor > minimum_impact_factor
    }
    if not eligible:
        return []

    seen: set[str] = set()
    papers: list[Paper] = []
    from_date = date.today() - timedelta(days=days_back)
    until_date = date.today()
    for keyword in keywords:
        for item in _query_crossref(keyword, from_date, until_date):
            paper = _parse_item(item, eligible, keywords)
            if paper is None or paper.id in seen:
                continue
            seen.add(paper.id)
            papers.append(paper)
        time.sleep(1)

    papers.sort(key=lambda item: (item.impact_factor, item.published), reverse=True)
    return papers[:max_items]


def _query_crossref(keyword: str, from_date: date, until_date: date) -> list[dict]:
    filters = ",".join(
        [
            "type:journal-article",
            f"from-pub-date:{from_date.isoformat()}",
            f"until-pub-date:{until_date.isoformat()}",
        ]
    )
    items: list[dict] = []
    seen: set[str] = set()
    for field in ("query.title", "query.bibliographic"):
        params = {
            field: keyword,
            "filter": filters,
            "rows": 100,
            "select": "DOI,title,author,container-title,published-print,published-online,published,abstract,URL,resource,link",
        }
        for item in _request_crossref(params):
            key = item.get("DOI") or item.get("URL") or _first(item.get("title"))
            if key in seen:
                continue
            seen.add(key)
            items.append(item)
        time.sleep(1)
    return items


def _request_crossref(params: dict[str, object]) -> list[dict]:
    mailto = os.environ.get("CROSSREF_MAILTO")
    if mailto:
        params["mailto"] = mailto
    request = Request(
        f"{CROSSREF_API}?{urlencode(params)}",
        headers={"User-Agent": "research-digest-mailer/0.1"},
    )
    for attempt in range(3):
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return payload.get("message", {}).get("items", [])
        except HTTPError as error:
            if error.code != 429 or attempt == 2:
                raise
            time.sleep(10 * (attempt + 1))
    return []


def _parse_item(
    item: dict,
    eligible_journals: dict[str, Journal],
    keywords: tuple[str, ...],
) -> Paper | None:
    journal_name = _first(item.get("container-title"))
    journal = eligible_journals.get(_normalize(journal_name))
    if journal is None:
        return None

    title = _clean_text(_first(item.get("title")))
    abstract = _clean_text(item.get("abstract", ""))
    haystack = f"{title} {abstract}".lower()
    matched = tuple(keyword for keyword in keywords if keyword.lower() in haystack)
    if not matched:
        return None

    doi = item.get("DOI", "")
    link = item.get("URL") or (f"https://doi.org/{doi}" if doi else "")
    published = _published_date(item)
    authors = tuple(_author_name(author) for author in item.get("author", [])[:8])
    source_urls = _source_urls(item, link)
    return Paper(
        id=doi or link or title,
        title=title,
        authors=tuple(author for author in authors if author),
        summary=abstract or "Crossref record does not include an abstract.",
        summary_zh="",
        published=published,
        link=link,
        image_url="",
        source_urls=source_urls,
        journal=journal.name,
        impact_factor=journal.impact_factor,
        matched_keywords=matched,
    )


def _published_date(item: dict) -> date:
    for key in ("published-online", "published-print", "published"):
        parts = item.get(key, {}).get("date-parts", [])
        if parts and parts[0]:
            year, month, day = (parts[0] + [1, 1])[:3]
            return date(int(year), int(month), int(day))
    return date.today()


def _author_name(author: dict) -> str:
    given = author.get("given", "")
    family = author.get("family", "")
    return " ".join(part for part in (given, family) if part)


def _source_urls(item: dict, fallback: str) -> tuple[str, ...]:
    urls: list[str] = []
    resource_url = item.get("resource", {}).get("primary", {}).get("URL")
    if resource_url:
        urls.append(resource_url)
    for link in item.get("link", []):
        url = link.get("URL")
        content_type = link.get("content-type", "")
        if url and ("html" in content_type or "xml" in content_type or content_type == "unspecified"):
            urls.append(url)
    if fallback:
        urls.append(fallback)
    seen: set[str] = set()
    unique = []
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        unique.append(url)
    return tuple(unique)


def _first(value: object) -> str:
    if isinstance(value, list) and value:
        return str(value[0])
    if isinstance(value, str):
        return value
    return ""


def _clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = unescape(value)
    return " ".join(value.split())


def _normalize(value: str) -> str:
    value = unescape(value)
    return re.sub(r"[^a-z0-9]+", "", value.lower())
