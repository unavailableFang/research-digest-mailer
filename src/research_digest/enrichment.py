from __future__ import annotations

from dataclasses import replace
from html import unescape
from html.parser import HTMLParser
import json
import os
import re
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from .crossref import Paper


class _MetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "meta":
            return
        data = {key.lower(): value or "" for key, value in attrs}
        key = data.get("property") or data.get("name")
        content = data.get("content")
        if key and content:
            self.meta[key.lower()] = unescape(content.strip())


def enrich_papers(papers: list[Paper], translate: bool = True) -> list[Paper]:
    return [enrich_paper(paper, translate=translate) for paper in papers]


def enrich_paper(paper: Paper, translate: bool = True) -> Paper:
    image_url = paper.image_url
    for source_url in paper.source_urls or (paper.link,):
        image_url = image_url or fetch_image_url(source_url)
        if image_url:
            break
    summary_zh = paper.summary_zh
    if translate and not summary_zh:
        summary_zh = translate_to_chinese(paper.summary)
    return replace(paper, image_url=image_url, summary_zh=summary_zh)


def fetch_image_url(url: str) -> str:
    if not url:
        return ""
    try:
        request = Request(
            url,
            headers={
                "User-Agent": "research-digest-mailer/0.1",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urlopen(request, timeout=20) as response:
            final_url = response.geturl()
            content_type = response.headers.get("content-type", "")
            if "html" not in content_type:
                return ""
            html = response.read(1_000_000).decode("utf-8", errors="ignore")
    except Exception:
        return ""

    parser = _MetaParser()
    parser.feed(html)
    for key in ("og:image", "twitter:image", "citation_image"):
        image_url = parser.meta.get(key)
        if image_url:
            return urljoin(final_url, image_url)
    return ""


def translate_to_chinese(text: str) -> str:
    text = " ".join(text.split())
    if not text or text == "Crossref record does not include an abstract.":
        return ""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return ""

    model = os.environ.get("OPENAI_MODEL", "gpt-5.5")
    prompt = (
        "请把下面的科研论文英文摘要翻译成简洁、准确、适合邮件阅读的中文。"
        "保留材料、器件、性能指标和专有名词的准确含义，不要添加原文没有的信息。\n\n"
        + _trim_for_translation(text)
    )
    payload = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            }
        ],
    }
    request = Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "research-digest-mailer/0.1",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception:
        return ""
    return _extract_response_text(data)


def _extract_response_text(data: dict) -> str:
    if isinstance(data.get("output_text"), str):
        return " ".join(data["output_text"].split())
    parts: list[str] = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str):
                parts.append(text)
    return " ".join(" ".join(parts).split())


def _trim_for_translation(text: str, limit: int = 2400) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."
