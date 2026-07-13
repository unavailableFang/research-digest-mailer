from __future__ import annotations

from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

from .crossref import Paper
from .config import DigestConfig


def render_subject(config: DigestConfig, now: datetime | None = None) -> str:
    current = now or datetime.now(ZoneInfo(config.timezone))
    return f"{config.title} | {current:%Y-%m-%d}"


def render_text(config: DigestConfig, papers: list[Paper], now: datetime | None = None) -> str:
    current = now or datetime.now(ZoneInfo(config.timezone))
    lines = [f"{config.title} - {current:%Y-%m-%d}", config.subtitle, ""]
    if not papers:
        lines.append("过去几天没有抓取到匹配的新发表论文。")
        return "\n".join(lines)

    for index, paper in enumerate(papers, start=1):
        authors = ", ".join(paper.authors[:4])
        if len(paper.authors) > 4:
            authors += " et al."
        lines.extend(
            [
                f"{index}. {paper.title}",
                f"   Journal: {paper.journal} (IF {paper.impact_factor:g})",
                f"   Keywords: {', '.join(paper.matched_keywords)}",
                f"   Authors: {authors or 'Unknown'}",
                f"   Published: {paper.published:%Y-%m-%d}",
                f"   Link: {paper.link}",
                f"   Summary: {paper.summary}",
                f"   中文摘要: {paper.summary_zh or '未配置翻译或翻译暂不可用'}",
                "",
            ]
        )
    return "\n".join(lines)


def render_html(config: DigestConfig, papers: list[Paper], now: datetime | None = None) -> str:
    current = now or datetime.now(ZoneInfo(config.timezone))
    items = "\n".join(_render_paper(index, paper) for index, paper in enumerate(papers, start=1))
    if not items:
        items = """
        <tr>
          <td class="empty">
            过去几天没有抓取到匹配的新发表论文。可以放宽关键词、延长回看天数，或补充更多影响因子大于 10 的期刊。
          </td>
        </tr>
        """

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(config.title)}</title>
  <style>
    body {{
      margin: 0;
      padding: 0;
      background: #f5f7fb;
      color: #162033;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, "PingFang SC", "Microsoft YaHei", sans-serif;
      line-height: 1.55;
    }}
    .shell {{
      width: 100%;
      background: #f5f7fb;
      padding: 24px 0;
    }}
    .container {{
      width: 680px;
      max-width: calc(100% - 24px);
      margin: 0 auto;
      background: #ffffff;
      border: 1px solid #dfe5ee;
      border-radius: 8px;
      overflow: hidden;
    }}
    .header {{
      padding: 28px 28px 18px;
      background: #102033;
      color: #ffffff;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 24px;
      line-height: 1.25;
      font-weight: 750;
      letter-spacing: 0;
    }}
    .subtitle {{
      margin: 0;
      color: #d6dee8;
      font-size: 14px;
    }}
    .meta {{
      margin-top: 14px;
      color: #aebdd0;
      font-size: 13px;
    }}
    .content {{
      width: 100%;
      border-collapse: collapse;
    }}
    .paper {{
      padding: 22px 28px;
      border-top: 1px solid #e7ecf3;
    }}
    .paper:first-child {{
      border-top: 0;
    }}
    .topic {{
      display: inline-block;
      margin-bottom: 10px;
      color: #185a9d;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }}
    h2 {{
      margin: 0 0 10px;
      font-size: 18px;
      line-height: 1.35;
      letter-spacing: 0;
    }}
    h2 a {{
      color: #162033;
      text-decoration: none;
    }}
    .authors, .date, .summary {{
      margin: 0 0 10px;
      color: #45546a;
      font-size: 14px;
    }}
    .media {{
      width: 188px;
      padding: 2px 0 0 18px;
      vertical-align: top;
    }}
    .media img {{
      display: block;
      width: 170px;
      max-width: 170px;
      height: auto;
      border: 1px solid #dfe5ee;
      border-radius: 6px;
    }}
    .summary {{
      color: #26364c;
    }}
    .summary-title {{
      margin: 14px 0 6px;
      color: #162033;
      font-size: 13px;
      font-weight: 700;
    }}
    .button {{
      display: inline-block;
      margin-top: 4px;
      padding: 10px 14px;
      background: #1e6bb8;
      color: #ffffff !important;
      border-radius: 6px;
      text-decoration: none;
      font-size: 14px;
      font-weight: 700;
    }}
    .empty {{
      padding: 28px;
      color: #45546a;
      font-size: 15px;
    }}
    .footer {{
      padding: 18px 28px 26px;
      color: #6d7b8f;
      font-size: 12px;
      background: #fbfcfe;
      border-top: 1px solid #e7ecf3;
    }}
    @media only screen and (max-width: 520px) {{
      .shell {{
        padding: 0;
      }}
      .container {{
        max-width: 100%;
        border-left: 0;
        border-right: 0;
        border-radius: 0;
      }}
      .header, .paper, .empty, .footer {{
        padding-left: 18px;
        padding-right: 18px;
      }}
      h1 {{
        font-size: 22px;
      }}
      h2 {{
        font-size: 17px;
      }}
      .button {{
        display: block;
        text-align: center;
      }}
      .summary-table,
      .summary-table tbody,
      .summary-table tr,
      .summary-table td {{
        display: block;
        width: 100% !important;
      }}
      .media {{
        padding: 0 0 12px;
      }}
      .media img {{
        width: 100%;
        max-width: 100%;
      }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <div class="container">
      <div class="header">
        <h1>{escape(config.title)}</h1>
        <p class="subtitle">{escape(config.subtitle)}</p>
        <div class="meta">{current:%Y-%m-%d %H:%M} · {escape(config.timezone)} · 共 {len(papers)} 条</div>
      </div>
      <table class="content" role="presentation">
        {items}
      </table>
      <div class="footer">
        数据源：Crossref 已发表期刊论文记录。影响因子来自 config/topics.toml 中的白名单，请按最新版 JCR 或期刊官网数据维护。
      </div>
    </div>
  </div>
</body>
</html>"""


def _render_paper(index: int, paper: Paper) -> str:
    authors = ", ".join(paper.authors[:5])
    if len(paper.authors) > 5:
        authors += " et al."
    summary_zh = paper.summary_zh or "未配置翻译或翻译暂不可用。"
    image_cell = ""
    if paper.image_url:
        image_cell = f"""
              <td class="media">
                <img src="{escape(paper.image_url)}" alt="{escape(paper.title)}">
              </td>
        """
    return f"""
        <tr>
          <td class="paper">
            <span class="topic">{index:02d} · IF {paper.impact_factor:g} · {escape(paper.journal)}</span>
            <h2><a href="{escape(paper.link)}">{escape(paper.title)}</a></h2>
            <p class="authors">{escape(authors or "Unknown authors")}</p>
            <p class="date">发表于 {paper.published:%Y-%m-%d} · 关键词：{escape(", ".join(paper.matched_keywords))}</p>
            <table class="summary-table" role="presentation" width="100%">
              <tr>
                <td>
                  <p class="summary-title">英文摘要</p>
                  <p class="summary">{escape(paper.summary)}</p>
                  <p class="summary-title">中文摘要</p>
                  <p class="summary">{escape(summary_zh)}</p>
                </td>
                {image_cell}
              </tr>
            </table>
            <a class="button" href="{escape(paper.link)}">打开论文</a>
          </td>
        </tr>
    """
