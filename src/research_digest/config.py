from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.9/3.10
    import tomli as tomllib


@dataclass(frozen=True)
class Journal:
    name: str
    impact_factor: float


@dataclass(frozen=True)
class DigestConfig:
    title: str
    subtitle: str
    timezone: str
    days_back: int
    max_items: int
    minimum_impact_factor: float
    keywords: tuple[str, ...]
    journals: tuple[Journal, ...]


def load_config(path: Path) -> DigestConfig:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    digest = data.get("digest", {})
    keywords = tuple(item.strip() for item in digest.get("keywords", []) if item.strip())
    journals = tuple(
        Journal(
            name=item["name"],
            impact_factor=float(item["impact_factor"]),
        )
        for item in data.get("journals", [])
    )
    if not keywords:
        raise ValueError("digest.keywords must contain at least one search phrase.")
    if not journals:
        raise ValueError("At least one [[journals]] entry is required.")

    return DigestConfig(
        title=digest.get("title", "Daily Research Digest"),
        subtitle=digest.get("subtitle", "New papers matching your topics"),
        timezone=digest.get("timezone", "Asia/Hong_Kong"),
        days_back=int(digest.get("days_back", 2)),
        max_items=int(digest.get("max_items", 12)),
        minimum_impact_factor=float(digest.get("minimum_impact_factor", 10)),
        keywords=keywords,
        journals=journals,
    )
