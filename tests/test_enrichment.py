import json
from urllib.parse import parse_qs

from research_digest.enrichment import fetch_image_url, translate_to_chinese


class _FakeResponse:
    def __init__(self, body: str, url: str = "https://www.nature.com/articles/example"):
        self._body = body.encode("utf-8")
        self._url = url
        self.headers = {"content-type": "text/html; charset=utf-8"}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def geturl(self):
        return self._url

    def read(self, *_args):
        return self._body


def test_fetch_image_url_uses_json_ld_article_image(monkeypatch):
    html = """
    <html>
      <head>
        <meta property="og:image" content="/static/logo.png">
        <script type="application/ld+json">
          {
            "@type": "ScholarlyArticle",
            "image": {
              "@type": "ImageObject",
              "url": "/articles/example/figures/1.png"
            }
          }
        </script>
      </head>
    </html>
    """

    monkeypatch.setattr(
        "research_digest.enrichment.urlopen",
        lambda *_args, **_kwargs: _FakeResponse(html),
    )

    assert fetch_image_url("https://doi.org/10.1038/example") == (
        "https://www.nature.com/articles/example/figures/1.png"
    )


def test_translate_to_chinese_uses_google_translation_api(monkeypatch):
    captured = {}

    def fake_urlopen(request, **_kwargs):
        captured["url"] = request.full_url
        captured["body"] = request.data.decode("utf-8")
        payload = {"data": {"translations": [{"translatedText": "中文摘要"}]}}
        return _FakeResponse(json.dumps(payload), url=request.full_url)

    monkeypatch.setenv("GOOGLE_TRANSLATE_API_KEY", "test-key")
    monkeypatch.setattr("research_digest.enrichment.urlopen", fake_urlopen)

    assert translate_to_chinese("An abstract about radiative cooling.") == "中文摘要"
    assert captured["url"] == "https://translation.googleapis.com/language/translate/v2"
    params = parse_qs(captured["body"])
    assert params["key"] == ["test-key"]
    assert params["target"] == ["zh-CN"]
    assert params["source"] == ["en"]
    assert params["format"] == ["text"]
    assert params["q"] == ["An abstract about radiative cooling."]
