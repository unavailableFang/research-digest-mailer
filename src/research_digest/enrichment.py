from __future__ import annotations

from dataclasses import replace
from html import unescape
from html.parser import HTMLParser
import json
import os
import re
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from .crossref import Paper


class _MetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, str] = {}
        self.link_images: list[str] = []
        self.images: list[tuple[str, str]] = []
        self.json_ld_blocks: list[str] = []
        self._script_type = ""
        self._script_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        data = {key.lower(): value or "" for key, value in attrs}
        if tag == "script":
            self._script_type = data.get("type", "").lower()
            self._script_parts = []
            return
        if tag == "meta":
            key = data.get("property") or data.get("name")
            content = data.get("content")
            if key and content:
                self.meta[key.lower()] = unescape(content.strip())
            return
        if tag == "link":
            rel = data.get("rel", "").lower()
            href = data.get("href", "")
            if href and any(name in rel for name in ("image_src", "preload")):
                if not rel or data.get("as", "").lower() in ("", "image") or "image_src" in rel:
                    self.link_images.append(unescape(href.strip()))
            return
        if tag == "img":
            src = (
                data.get("src")
                or data.get("data-src")
                or data.get("data-original")
                or data.get("data-lazy-src")
                or data.get("data-image")
            )
            if src:
                context = " ".join(
                    data.get(key, "")
                    for key in ("alt", "title", "class", "id", "src")
                    if data.get(key)
                )
                self.images.append((unescape(src.strip()), unescape(context.strip())))

    def handle_data(self, data: str) -> None:
        if self._script_type == "application/ld+json":
            self._script_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._script_type == "application/ld+json":
            block = "".join(self._script_parts).strip()
            if block:
                self.json_ld_blocks.append(block)
        if tag.lower() == "script":
            self._script_type = ""
            self._script_parts = []


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
    for key in (
        "citation_image",
        "dc.source.image",
        "prism.image",
        "og:image",
        "og:image:url",
        "og:image:secure_url",
        "twitter:image",
        "twitter:image:src",
    ):
        image_url = parser.meta.get(key)
        if image_url and _looks_like_article_image(image_url):
            return urljoin(final_url, image_url)
    for image_url in _json_ld_images(parser.json_ld_blocks):
        if image_url and _looks_like_article_image(image_url):
            return urljoin(final_url, image_url)
    for image_url in parser.link_images:
        if image_url and _looks_like_article_image(image_url):
            return urljoin(final_url, image_url)
    best = _best_html_image(parser.images)
    if best:
        return urljoin(final_url, best)
    return ""


def translate_to_chinese(text: str) -> str:
    text = " ".join(text.split())
    if not text or text == "Crossref record does not include an abstract.":
        return ""
    api_key = os.environ.get("GOOGLE_TRANSLATE_API_KEY") or os.environ.get(
        "GOOGLE_TRANSLATION_API_KEY"
    )
    if not api_key:
        return ""

    payload = urlencode(
        {
            "q": text,
            "target": os.environ.get("GOOGLE_TRANSLATE_TARGET", "zh-CN"),
            "source": os.environ.get("GOOGLE_TRANSLATE_SOURCE", "en"),
            "format": "text",
            "key": api_key,
        }
    ).encode("utf-8")
    request = Request(
        "https://translation.googleapis.com/language/translate/v2",
        data=payload,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "research-digest-mailer/0.1",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception:
        return ""
    translations = data.get("data", {}).get("translations", [])
    if not translations:
        return ""
    translated = translations[0].get("translatedText", "")
    return " ".join(unescape(translated).split())


def _json_ld_images(blocks: list[str]) -> list[str]:
    images: list[str] = []
    for block in blocks:
        try:
            payload = json.loads(block)
        except json.JSONDecodeError:
            continue
        images.extend(_extract_json_images(payload))
    return images


def _extract_json_images(value: object) -> list[str]:
    if isinstance(value, dict):
        images: list[str] = []
        image = value.get("image") or value.get("thumbnailUrl")
        kind = value.get("@type", "")
        kinds = {kind.lower()} if isinstance(kind, str) else set()
        if isinstance(kind, list):
            kinds = {str(item).lower() for item in kind}
        if "imageobject" in kinds:
            image = image or value.get("contentUrl") or value.get("url")
        if isinstance(image, str):
            images.append(image)
        elif isinstance(image, list):
            for item in image:
                images.extend(_extract_json_images(item))
        elif isinstance(image, dict):
            images.extend(_extract_json_images(image))
        for key in ("@graph", "mainEntity", "hasPart"):
            images.extend(_extract_json_images(value.get(key)))
        return images
    if isinstance(value, list):
        images = []
        for item in value:
            images.extend(_extract_json_images(item))
        return images
    return []


def _best_html_image(images: list[tuple[str, str]]) -> str:
    best_url = ""
    best_score = 0
    for url, context in images:
        if not _looks_like_article_image(url):
            continue
        score = _image_score(url, context)
        if score > best_score:
            best_url = url
            best_score = score
    return best_url


def _looks_like_article_image(url: str) -> bool:
    value = url.lower()
    if not value or value.startswith("data:"):
        return False
    blocked = (
        "logo",
        "icon",
        "sprite",
        "avatar",
        "profile",
        "placeholder",
        "transparent",
        "tracking",
        "pixel",
        "ads",
        "advert",
    )
    return not any(token in value for token in blocked)


def _image_score(url: str, context: str) -> int:
    haystack = f"{url} {context}".lower()
    score = 1
    for token in (
        "figure",
        "fig",
        "article",
        "main",
        "media",
        "image",
        "graphic",
        "graphical",
        "abstract",
        "thumbnail",
        "featured",
        "asset",
        "nature.com/articles",
    ):
        if token in haystack:
            score += 2
    if re.search(r"\.(jpg|jpeg|png|webp)(\?|$)", haystack):
        score += 2
    if "supplementary" in haystack or "author" in haystack:
        score -= 2
    return score
