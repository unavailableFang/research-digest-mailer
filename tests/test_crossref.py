from research_digest.config import Journal
from research_digest.crossref import _parse_item


def test_parse_item_matches_html_entity_journal_name():
    item = {
        "DOI": "10.1038/s41377-026-02391-6",
        "title": [
            "Subambient daytime radiative cooling to mitigate haze-induced amplification of urban heat islands"
        ],
        "container-title": ["Light: Science &amp; Applications"],
        "published-online": {"date-parts": [[2026, 6, 23]]},
        "abstract": "Passive daytime radiative cooling technology for urban heat islands.",
        "URL": "https://doi.org/10.1038/s41377-026-02391-6",
    }
    journals = {
        "lightscienceapplications": Journal(
            name="Light: Science & Applications",
            impact_factor=24.0,
        )
    }

    paper = _parse_item(item, journals, ("radiative cooling",))

    assert paper is not None
    assert paper.journal == "Light: Science & Applications"
    assert paper.impact_factor == 24.0
    assert paper.matched_keywords == ("radiative cooling",)
    assert paper.summary_zh == ""
    assert paper.image_url == ""
    assert paper.source_urls == ("https://doi.org/10.1038/s41377-026-02391-6",)
