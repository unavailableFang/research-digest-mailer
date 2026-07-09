from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path

from .crossref import Paper


@dataclass
class SentState:
    path: Path
    sent: dict[str, str]


def load_state(path: Path) -> SentState:
    if not path.exists():
        return SentState(path=path, sent={})
    data = json.loads(path.read_text(encoding="utf-8"))
    sent = data.get("sent", {}) if isinstance(data, dict) else {}
    return SentState(path=path, sent={str(key): str(value) for key, value in sent.items()})


def filter_unsent(papers: list[Paper], state: SentState) -> list[Paper]:
    return [paper for paper in papers if paper.id not in state.sent]


def mark_sent(papers: list[Paper], state: SentState, sent_at: datetime) -> None:
    if not papers:
        return
    state.path.parent.mkdir(parents=True, exist_ok=True)
    for paper in papers:
        state.sent[paper.id] = sent_at.isoformat()
    payload = {"sent": dict(sorted(state.sent.items()))}
    state.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
