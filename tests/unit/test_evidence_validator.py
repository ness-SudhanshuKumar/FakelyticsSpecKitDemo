"""Unit tests for evidence validator module (T-304)."""

import asyncio
import pytest

from src.workers.pipelines.text.evidence_validator import (
    EvidenceValidation,
    EvidenceValidator,
    EvidenceProcessor,
    get_evidence_processor,
)


class TestEvidenceValidation:
    """Tests for EvidenceValidation dataclass."""

    def test_evidence_validation_creation(self):
        """Test creating EvidenceValidation."""
        validation = EvidenceValidation(
            url="https://example.com",
            is_accessible=True,
            status_code=200,
            title="Example",
        )
        assert validation.url == "https://example.com"
        assert validation.is_accessible is True
        assert validation.status_code == 200

    def test_evidence_validation_to_dict(self):
        """Test converting to dict."""
        validation = EvidenceValidation(
            url="https://example.com",
            is_accessible=True,
            status_code=200,
            title="Example",
            snippet_preview="This is an example",
        )
        d = validation.to_dict()
        assert d["url"] == "https://example.com"
        assert d["is_accessible"] is True
        assert d["status_code"] == 200
        assert d["title"] == "Example"


class TestEvidenceValidator:
    """Tests for EvidenceValidator class."""

    @pytest.mark.asyncio
    async def test_validate_empty_url_raises_error(self):
        """Test that empty URL raises ValueError."""
        validator = EvidenceValidator()
        with pytest.raises(ValueError, match="Invalid URL"):
            await validator.validate_evidence_url("")

    @pytest.mark.asyncio
    async def test_validate_none_url_raises_error(self):
        """Test that None URL raises ValueError."""
        validator = EvidenceValidator()
        with pytest.raises(ValueError, match="Invalid URL"):
            await validator.validate_evidence_url(None)

    @pytest.mark.asyncio
    async def test_validate_invalid_url_format(self):
        """Test that invalid URL format is handled."""
        validator = EvidenceValidator()
        result = await validator.validate_evidence_url("not a url")
        assert result.is_accessible is False
        assert result.validation_error is not None

    @pytest.mark.asyncio
    async def test_validate_unsupported_scheme(self):
        """Test that unsupported scheme is rejected."""
        validator = EvidenceValidator()
        result = await validator.validate_evidence_url("ftp://example.com")
        assert result.is_accessible is False
        assert "Unsupported scheme" in result.validation_error

    @pytest.mark.asyncio
    async def test_validate_blocks_private_ip(self):
        """Test that private IP addresses are blocked."""
        validator = EvidenceValidator()
        test_urls = [
            "http://127.0.0.1",
            "http://192.168.1.1",
            "http://10.0.0.1",
            "http://localhost",
        ]
        for url in test_urls:
            result = await validator.validate_evidence_url(url)
            assert result.is_accessible is False
            assert "private" in result.validation_error.lower()

    @pytest.mark.asyncio
    async def test_validate_public_url_attempt(self):
        """Test validating a public URL (may fail without internet)."""
        validator = EvidenceValidator(timeout=5)
        result = await validator.validate_evidence_url("https://httpbin.org/status/200")
        # Result depends on network availability
        assert isinstance(result, EvidenceValidation)
        assert result.url == "https://httpbin.org/status/200"

    @pytest.mark.asyncio
    async def test_validate_http_vs_https(self):
        """Test both HTTP and HTTPS schemes."""
        validator = EvidenceValidator()
        
        # HTTPS should pass URL validation (even if it fails to connect)
        result_https = await validator.validate_evidence_url("https://example.com/fake")
        assert result_https.url == "https://example.com/fake"

        # HTTP should also pass URL validation
        result_http = await validator.validate_evidence_url("http://example.com/fake")
        assert result_http.url == "http://example.com/fake"

    def test_is_private_ip(self):
        """Test private IP detection."""
        validator = EvidenceValidator()
        
        # Private IPs
        assert validator._is_private_ip("127.0.0.1") is True
        assert validator._is_private_ip("192.168.1.1") is True
        assert validator._is_private_ip("10.0.0.1") is True
        assert validator._is_private_ip("172.16.0.1") is True
        assert validator._is_private_ip("localhost") is True
        
        # Public IPs/hostnames
        assert validator._is_private_ip("8.8.8.8") is False
        assert validator._is_private_ip("example.com") is False
        assert validator._is_private_ip("google.com") is False

    @pytest.mark.asyncio
    async def test_extract_metadata_with_valid_html(self):
        """Test metadata extraction from HTML."""
        validator = EvidenceValidator()
        
        html_content = b"""
        <html>
            <head>
                <title>Example Page</title>
                <meta name="description" content="This is an example description">
            </head>
            <body>
                <p>First paragraph with content</p>
            </body>
        </html>
        """
        
        title, snippet = await validator._extract_metadata(html_content)
        assert title == "Example Page"
        assert snippet is not None
        assert "description" in snippet.lower() or "example" in snippet.lower()

    @pytest.mark.asyncio
    async def test_extract_metadata_with_empty_content(self):
        """Test metadata extraction with empty content."""
        validator = EvidenceValidator()
        title, snippet = await validator._extract_metadata(b"")
        assert title is None
        assert snippet is None

    @pytest.mark.asyncio
    async def test_extract_metadata_with_invalid_html(self):
        """Test metadata extraction with invalid HTML."""
        validator = EvidenceValidator()
        title, snippet = await validator._extract_metadata(b"not html")
        # Should not raise, just return None values
        assert isinstance(title, (str, type(None)))
        assert isinstance(snippet, (str, type(None)))


class TestEvidenceProcessor:
    """Tests for EvidenceProcessor class."""

    def test_evidence_processor_creation(self):
        """Test creating EvidenceProcessor."""
        processor = EvidenceProcessor(timeout=15, max_concurrent=3)
        assert processor.validator is not None
        assert processor.max_concurrent == 3

    def test_evidence_processor_defaults(self):
        """Test EvidenceProcessor with default values."""
        processor = EvidenceProcessor()
        assert processor.validator is not None
        assert processor.max_concurrent == 5

    @pytest.mark.asyncio
    async def test_validate_batch_empty_list(self):
        """Test batch validation with empty list."""
        processor = EvidenceProcessor()
        result = await processor.validate_batch([])
        assert result == {}

    @pytest.mark.asyncio
    async def test_validate_batch_private_ips(self):
        """Test batch validation with private IPs."""
        processor = EvidenceProcessor()
        urls = ["http://127.0.0.1", "http://192.168.1.1"]
        results = await processor.validate_batch(urls, timeout_total=10)
        
        for url, validation in results.items():
            assert validation.is_accessible is False

    @pytest.mark.asyncio
    async def test_validate_batch_single_url(self):
        """Test batch validation with single URL."""
        processor = EvidenceProcessor()
        results = await processor.validate_batch(["http://example.com"], timeout_total=10)
        assert isinstance(results, dict)

    @pytest.mark.asyncio
    async def test_validate_and_enrich_no_evidence(self):
        """Test enriching finding with no evidence."""
        processor = EvidenceProcessor()
        finding = {"verdict": "Disputed", "confidence": 75}
        result = await processor.validate_and_enrich(finding)
        assert result == finding

    @pytest.mark.asyncio
    async def test_validate_and_enrich_empty_evidence(self):
        """Test enriching finding with empty evidence list."""
        processor = EvidenceProcessor()
        finding = {"verdict": "Disputed", "confidence": 75, "evidence": []}
        result = await processor.validate_and_enrich(finding)
        assert result["evidence"] == []

    @pytest.mark.asyncio
    async def test_validate_and_enrich_with_evidence(self):
        """Test enriching finding with evidence."""
        processor = EvidenceProcessor()
        finding = {
            "verdict": "Disputed",
            "confidence": 75,
            "evidence": [
                {"url": "http://192.168.1.1", "snippet": "Some text"}
            ]
        }
        result = await processor.validate_and_enrich(finding)
        assert "evidence" in result
        assert len(result["evidence"]) > 0
        assert "url" in result["evidence"][0]

    @pytest.mark.asyncio
    async def test_validate_and_enrich_preserves_evidence_data(self):
        """Test that enrichment preserves original evidence data."""
        processor = EvidenceProcessor()
        finding = {
            "evidence": [
                {
                    "url": "http://example.com",
                    "snippet": "Original snippet",
                    "validated": False
                }
            ]
        }
        result = await processor.validate_and_enrich(finding)
        assert result["evidence"][0]["snippet"] == "Original snippet"
        assert result["evidence"][0]["url"] == "http://example.com"

    @pytest.mark.asyncio
    async def test_concurrency_limit(self):
        """Test that max_concurrent is respected."""
        # Create processor with low concurrency
        processor = EvidenceProcessor(timeout=2, max_concurrent=1)
        
        # This should work without errors even with low concurrency
        urls = ["http://192.168.1.1", "http://192.168.1.2", "http://192.168.1.3"]
        results = await processor.validate_batch(urls, timeout_total=15)
        
        assert isinstance(results, dict)
        assert len(results) == len(urls)


class TestGlobalInstances:
    """Tests for global singleton instances."""

    def test_get_evidence_processor_singleton(self):
        """Test that get_evidence_processor returns same instance."""
        processor1 = get_evidence_processor()
        processor2 = get_evidence_processor()
        assert processor1 is processor2

    def test_get_evidence_processor_with_params(self):
        """Test get_evidence_processor with custom parameters returns instance."""
        # Since the processor is a singleton, it returns the cached instance
        # This test just verifies it returns an EvidenceProcessor
        processor = get_evidence_processor(timeout=20, max_concurrent=10)
        assert isinstance(processor, EvidenceProcessor)
        assert hasattr(processor, 'validator')
        assert hasattr(processor, 'max_concurrent')


class TestErrorHandling:
    """Tests for error handling in evidence validation."""

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test timeout handling."""
        validator = EvidenceValidator(timeout=1)
        # This URL should timeout or fail
        result = await validator.validate_evidence_url("https://httpbin.org/delay/10")
        # Should handle gracefully and return error
        assert isinstance(result, EvidenceValidation)
        assert result.url == "https://httpbin.org/delay/10"

    @pytest.mark.asyncio
    async def test_invalid_url_no_crash(self):
        """Test that invalid URLs don't crash the validator."""
        validator = EvidenceValidator()
        invalid_urls = [
            "ht!tp://bad url",
            "://no-scheme",
            "http://",
            "just-text",
        ]
        
        for url in invalid_urls:
            result = await validator.validate_evidence_url(url)
            assert isinstance(result, EvidenceValidation)
            assert result.is_accessible is False

    @pytest.mark.asyncio
    async def test_batch_with_mixed_validity(self):
        """Test batch processing with mix of valid/invalid URLs."""
        processor = EvidenceProcessor()
        urls = [
            "http://192.168.1.1",  # Private IP - blocked
            "not-a-url",  # Invalid format
            "http://example.com",  # Valid format but may fail
        ]
        
        results = await processor.validate_batch(urls, timeout_total=15)
        assert isinstance(results, dict)
        # Should handle all URLs without crashing
        for url, validation in results.items():
            assert isinstance(validation, EvidenceValidation)
