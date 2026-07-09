from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from .crossref import fetch_all
from .config import load_config
from .email_render import render_html, render_subject, render_text
from .enrichment import enrich_papers
from .mailer import load_mail_settings, send_email
from .state import filter_unsent, load_state, mark_sent


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a daily research digest email.")
    parser.add_argument(
        "--config",
        default=os.environ.get("DIGEST_CONFIG", "config/topics.toml"),
        help="Path to digest TOML config.",
    )
    parser.add_argument(
        "--preview",
        default=os.environ.get("DIGEST_PREVIEW", ""),
        help="Write the HTML email to this path instead of sending.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=os.environ.get("DIGEST_DRY_RUN", "").lower() in {"1", "true", "yes"},
        help="Print the text email to stdout instead of sending.",
    )
    parser.add_argument(
        "--state-file",
        default=os.environ.get("DIGEST_STATE_FILE", ".digest-state/sent.json"),
        help="Path used to remember already-sent paper IDs.",
    )
    parser.add_argument(
        "--include-sent",
        action="store_true",
        default=os.environ.get("DIGEST_INCLUDE_SENT", "").lower() in {"1", "true", "yes"},
        help="Include papers even if they are already recorded as sent.",
    )
    parser.add_argument(
        "--skip-translation",
        action="store_true",
        default=os.environ.get("DIGEST_SKIP_TRANSLATION", "").lower() in {"1", "true", "yes"},
        help="Do not call the optional translation provider.",
    )
    args = parser.parse_args()

    config = load_config(Path(args.config))
    now = datetime.now(ZoneInfo(config.timezone))
    state = load_state(Path(args.state_file))
    should_apply_state = not args.preview and not args.dry_run and not args.include_sent
    fetch_limit = config.max_items * 3 if should_apply_state else config.max_items
    papers = fetch_all(
        config.keywords,
        config.journals,
        config.days_back,
        fetch_limit,
        config.minimum_impact_factor,
    )
    if should_apply_state:
        papers = filter_unsent(papers, state)[: config.max_items]
    papers = enrich_papers(papers, translate=not args.skip_translation)
    subject = render_subject(config, now)
    text = render_text(config, papers, now)
    html = render_html(config, papers, now)

    if args.preview:
        Path(args.preview).write_text(html, encoding="utf-8")
        print(f"Wrote HTML preview: {args.preview}")
        return

    if args.dry_run:
        print(f"Subject: {subject}\n")
        print(text)
        return

    settings = load_mail_settings()
    send_email(settings, subject, text, html)
    mark_sent(papers, state, now)
    print(f"Sent {len(papers)} papers to {', '.join(settings.recipients)}")


if __name__ == "__main__":
    main()
