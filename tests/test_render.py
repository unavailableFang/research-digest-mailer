from datetime import datetime, timezone

from research_digest.crossref import Paper
from research_digest.config import DigestConfig, Journal
from research_digest.email_render import render_html, render_subject, render_text


def test_render_subject_uses_configured_title_and_date():
    config = _config()
    subject = render_subject(config, datetime(2026, 7, 8, tzinfo=timezone.utc))

    assert subject == "每日科研进展 | 2026-07-08"


def test_render_outputs_responsive_html_and_plain_text():
    config = _config()
    paper = Paper(
        id="10.0000/example",
        title="Thermochromic Smart Windows with Improved Solar Modulation",
        authors=("Ada Lovelace", "Qian Wang"),
        summary="A concise abstract about smart-window materials and optical spectra.",
        summary_zh="一段关于智能窗材料和光谱的中文摘要。",
        published=datetime(2026, 7, 8, tzinfo=timezone.utc).date(),
        link="https://doi.org/10.0000/example",
        image_url="https://example.com/image.jpg",
        source_urls=("https://doi.org/10.0000/example",),
        journal="Advanced Materials",
        impact_factor=27.4,
        matched_keywords=("smart window",),
    )

    html = render_html(config, [paper], datetime(2026, 7, 8, tzinfo=timezone.utc))
    text = render_text(config, [paper], datetime(2026, 7, 8, tzinfo=timezone.utc))

    assert '@media only screen and (max-width: 520px)' in html
    assert "打开论文" in html
    assert "中文摘要" in html
    assert "https://example.com/image.jpg" in html
    assert "Thermochromic Smart Windows" in text
    assert "中文摘要" in text


def _config():
    return DigestConfig(
        title="每日科研进展",
        subtitle="自动汇总",
        timezone="UTC",
        days_back=2,
        max_items=12,
        minimum_impact_factor=10,
        keywords=("smart window",),
        journals=(Journal(name="Advanced Materials", impact_factor=27.4),),
    )
