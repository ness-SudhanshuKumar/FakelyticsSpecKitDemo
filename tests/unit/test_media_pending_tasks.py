"""Tests for pending media, URL validation, and rate-limit task coverage."""

import shutil
from pathlib import Path

import pytest

from src.api.dependencies.security import AuthContext, InMemoryRateLimiter, enforce_rate_limit
from src.core.extraction.service import ContentExtractionService, MediaItem, URLValidationError
from src.workers.pipelines.audio_video import analyze_audio_video
from src.workers.pipelines.image import analyze_images


class DummyResponse:
    def __init__(self):
        self.headers = {}


class FakeDownloadResponse:
    status = 200
    headers = {"Content-Type": "image/png", "Content-Length": "8"}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def read(self):
        return b"\x89PNGtest"


class FakeSession:
    def get(self, *args, **kwargs):
        return FakeDownloadResponse()


def test_url_validation_blocks_private_and_reserved_hosts():
    service = ContentExtractionService()

    for url in (
        "http://127.0.0.1/page",
        "http://192.168.1.10/page",
        "http://localhost/page",
        "http://example/page",
        "ftp://example.com/file",
        "https://user:pass@example.com/file",
    ):
        with pytest.raises(URLValidationError):
            service._validate_url(url)


@pytest.mark.asyncio
async def test_parse_content_prefers_json_ld_article_body_over_page_noise():
    service = ContentExtractionService()
    article_body = " ".join(["Main verified article sentence about the policy decision."] * 12)
    html = f"""
    <html>
      <head>
        <script type="application/ld+json">
        {{
          "@type": "NewsArticle",
          "headline": "Important policy decision",
          "description": "Concise article summary",
          "articleBody": "{article_body}"
        }}
        </script>
      </head>
      <body>
        <nav>Home Politics Sports Entertainment</nav>
        <aside>Related stories should not dominate extraction</aside>
        <article><p>Short visible teaser.</p></article>
      </body>
    </html>
    """

    extract = await service._parse_content("https://example.com/story", html)

    assert "Important policy decision" in extract.text_content
    assert "Main verified article sentence" in extract.text_content
    assert "Related stories" not in extract.text_content


@pytest.mark.asyncio
async def test_parse_content_removes_ads_and_related_from_semantic_article():
    service = ContentExtractionService()
    paragraph = " ".join(["The main report explains the event with enough detail for verification."] * 8)
    html = f"""
    <html>
      <body>
        <header>Site navigation</header>
        <article>
          <h1>Primary article headline</h1>
          <div class="advertisement">Buy now unrelated ad text</div>
          <p>{paragraph}</p>
          <div class="related">Related suggestion should disappear</div>
        </article>
        <footer>Footer links</footer>
      </body>
    </html>
    """

    extract = await service._parse_content("https://example.com/story", html)

    assert "Primary article headline" in extract.text_content
    assert "main report explains" in extract.text_content
    assert "Buy now" not in extract.text_content
    assert "Related suggestion" not in extract.text_content


@pytest.mark.asyncio
async def test_parse_content_extracts_direct_audio_and_video_src():
    service = ContentExtractionService()
    html = """
    <html>
      <body>
        <img src="/image.png" alt="News image">
        <audio src="/clip.mp3" title="Interview"></audio>
        <video src="/clip.mp4" title="Footage"></video>
      </body>
    </html>
    """

    extract = await service._parse_content("https://example.com/story", html)

    assert extract.images[0].url == "https://example.com/image.png"
    assert extract.audio[0].url == "https://example.com/clip.mp3"
    assert extract.video[0].url == "https://example.com/clip.mp4"


@pytest.mark.asyncio
async def test_download_media_item_sets_local_storage_metadata():
    service = ContentExtractionService()
    service.media_dir = Path("extracted_media_test")
    item = MediaItem(url="https://example.com/image.png", media_type="image")

    try:
        result = await service.download_media_item(FakeSession(), item)

        assert result.local_path
        assert result.storage_path.startswith("media/image/")
        assert result.content_type == "image/png"
        assert result.size_bytes == 8
        assert result.download_error is None
    finally:
        shutil.rmtree(service.media_dir, ignore_errors=True)


def test_image_analyzer_reports_download_and_forensics_details():
    item = MediaItem(
        url="https://example.com/ai-generated-image.png",
        media_type="image",
        local_path="extracted_media/image/sample.png",
        size_bytes=1024,
    )

    result = analyze_images([item])

    assert result.verdict == "Disputed"
    assert result.findings[0].details["forensics"]["downloaded_count"] == 1
    assert result.findings[0].details["reverse_search_status"] == "not_configured"


def test_audio_video_analyzer_reports_feature_summary():
    audio = MediaItem(
        url="https://example.com/interview.mp3",
        media_type="audio",
        local_path="extracted_media/audio/sample.mp3",
        size_bytes=2048,
    )
    video = MediaItem(url="https://example.com/deepfake-clip.mp4", media_type="video")

    result = analyze_audio_video([audio], [video])

    assert result.verdict == "Disputed"
    features = result.findings[0].details["feature_extraction"]
    assert features["audio_items"] == 1
    assert features["video_items"] == 1
    assert features["downloaded_audio"] == 1


def test_rate_limiter_allows_request_that_consumes_last_quota(monkeypatch):
    limiter = InMemoryRateLimiter()
    monkeypatch.setattr("src.api.dependencies.security.rate_limiter", limiter)

    response = DummyResponse()
    auth = AuthContext(api_key="dev-key", tier="free", daily_limit=1)

    enforce_rate_limit(response=response, auth=auth, endpoint="/verify")

    assert response.headers["X-RateLimit-Remaining"] == "0"

    with pytest.raises(Exception) as exc_info:
        enforce_rate_limit(response=DummyResponse(), auth=auth, endpoint="/verify")

    assert getattr(exc_info.value, "status_code", None) == 429
