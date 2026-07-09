from datetime import date, datetime, timezone

from research_digest.crossref import Paper
from research_digest.state import filter_unsent, load_state, mark_sent


def test_state_filters_and_records_sent_papers(tmp_path):
    state_path = tmp_path / "sent.json"
    paper = _paper("10.0000/example")
    other = _paper("10.0000/other")

    state = load_state(state_path)
    assert filter_unsent([paper, other], state) == [paper, other]

    mark_sent([paper], state, datetime(2026, 7, 8, tzinfo=timezone.utc))
    reloaded = load_state(state_path)

    assert filter_unsent([paper, other], reloaded) == [other]


def _paper(identifier: str) -> Paper:
    return Paper(
        id=identifier,
        title="Example",
        authors=(),
        summary="Abstract",
        summary_zh="摘要",
        published=date(2026, 7, 8),
        link=f"https://doi.org/{identifier}",
        image_url="",
        source_urls=(f"https://doi.org/{identifier}",),
        journal="Nature",
        impact_factor=56.1,
        matched_keywords=("radiative cooling",),
    )
