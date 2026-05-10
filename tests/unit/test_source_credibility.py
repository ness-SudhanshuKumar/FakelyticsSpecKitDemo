"""Unit tests for source credibility module (T-601)."""

import pytest

from src.workers.pipelines.spam.source_credibility import (
    SourceCredibility,
    SSLInfo,
    DomainInfo,
    SourceCredibilityScore,
    DomainReputation,
    SourceCredibilityAnalyzer,
    get_source_analyzer,
    analyze_source_credibility,
)


class TestSSLInfo:
    """Tests for SSLInfo dataclass."""

    def test_ssl_info_with_ssl(self):
        """Test creating SSLInfo with SSL."""
        ssl = SSLInfo(
            has_ssl=True,
            is_valid=True,
            protocol_version="TLS 1.3"
        )
        assert ssl.has_ssl is True
        assert ssl.is_valid is True

    def test_ssl_info_without_ssl(self):
        """Test creating SSLInfo without SSL."""
        ssl = SSLInfo(has_ssl=False, is_valid=False)
        assert ssl.has_ssl is False
        assert ssl.is_valid is False

    def test_ssl_info_to_dict(self):
        """Test converting SSLInfo to dict."""
        ssl = SSLInfo(has_ssl=True, is_valid=True, protocol_version="TLS 1.3")
        d = ssl.to_dict()
        assert d["has_ssl"] is True
        assert d["is_valid"] is True


class TestDomainInfo:
    """Tests for DomainInfo dataclass."""

    def test_domain_info_creation(self):
        """Test creating DomainInfo."""
        info = DomainInfo(
            domain="example.com",
            is_registered=True,
            age_years=10.0
        )
        assert info.domain == "example.com"
        assert info.age_years == 10.0

    def test_domain_info_to_dict(self):
        """Test converting DomainInfo to dict."""
        info = DomainInfo(
            domain="example.com",
            is_registered=True,
            age_years=5.0,
            is_typosquat=False
        )
        d = info.to_dict()
        assert d["domain"] == "example.com"
        assert d["age_years"] == 5.0


class TestSourceCredibilityScore:
    """Tests for SourceCredibilityScore dataclass."""

    def test_score_creation(self):
        """Test creating SourceCredibilityScore."""
        score = SourceCredibilityScore(
            domain="example.com",
            credibility_level=SourceCredibility.CREDIBLE,
            credibility_score=75,
            ssl_info=SSLInfo(has_ssl=True, is_valid=True),
            domain_info=DomainInfo(domain="example.com", is_registered=True),
            reputation_score=70,
            trust_indicators=["HTTPS enabled"],
            risk_indicators=[],
            summary="Credible source"
        )
        assert score.credibility_score == 75
        assert score.credibility_level == SourceCredibility.CREDIBLE

    def test_score_to_dict(self):
        """Test converting score to dict."""
        score = SourceCredibilityScore(
            domain="example.com",
            credibility_level=SourceCredibility.HIGHLY_CREDIBLE,
            credibility_score=90,
            ssl_info=SSLInfo(has_ssl=True, is_valid=True),
            domain_info=DomainInfo(domain="example.com", is_registered=True),
            reputation_score=85,
            trust_indicators=["HTTPS", "Trusted domain"],
            risk_indicators=[],
            summary="Highly credible"
        )
        d = score.to_dict()
        assert d["credibility_level"] == "highly_credible"
        assert d["credibility_score"] == 90


class TestDomainReputation:
    """Tests for DomainReputation class."""

    def test_check_trusted_domain_exact_match(self):
        """Test checking trusted domain with exact match."""
        score = DomainReputation.check_trusted_domain("wikipedia.org")
        assert score == 95

    def test_check_trusted_domain_tld_match(self):
        """Test checking domain by TLD."""
        score = DomainReputation.check_trusted_domain("test.edu")
        assert score == 80

    def test_check_untrusted_domain(self):
        """Test checking untrusted domain."""
        score = DomainReputation.check_trusted_domain("random-domain-xyz.net")
        assert score is None

    def test_detect_typosquatting_obvious(self):
        """Test detecting obvious typosquats."""
        assert DomainReputation.detect_typosquatting("goggle.com") is True
        assert DomainReputation.detect_typosquatting("faecbook.com") is True

    def test_detect_typosquatting_patterns(self):
        """Test detecting typosquat patterns."""
        assert DomainReputation.detect_typosquatting("admin-login.com") is True
        assert DomainReputation.detect_typosquatting("verify-account.com") is True

    def test_normal_domain_not_typosquat(self):
        """Test that normal domains aren't flagged."""
        assert DomainReputation.detect_typosquatting("google.com") is False
        assert DomainReputation.detect_typosquatting("wikipedia.org") is False


class TestSourceCredibilityAnalyzer:
    """Tests for SourceCredibilityAnalyzer class."""

    @pytest.mark.asyncio
    async def test_analyze_empty_url_raises_error(self):
        """Test that empty URL raises ValueError."""
        analyzer = SourceCredibilityAnalyzer()
        with pytest.raises(ValueError, match="Invalid URL"):
            await analyzer.analyze_url("")

    @pytest.mark.asyncio
    async def test_analyze_none_url_raises_error(self):
        """Test that None URL raises ValueError."""
        analyzer = SourceCredibilityAnalyzer()
        with pytest.raises(ValueError, match="Invalid URL"):
            await analyzer.analyze_url(None)

    @pytest.mark.asyncio
    async def test_analyze_invalid_url_format(self):
        """Test that invalid URL format raises ValueError."""
        analyzer = SourceCredibilityAnalyzer()
        with pytest.raises(ValueError):
            await analyzer.analyze_url("not-a-url")

    @pytest.mark.asyncio
    async def test_analyze_https_url(self):
        """Test analyzing HTTPS URL."""
        analyzer = SourceCredibilityAnalyzer()
        score = await analyzer.analyze_url("https://wikipedia.org/wiki/Test")
        assert isinstance(score, SourceCredibilityScore)
        assert score.ssl_info.has_ssl is True
        assert score.ssl_info.is_valid is True

    @pytest.mark.asyncio
    async def test_analyze_http_url(self):
        """Test analyzing HTTP URL."""
        analyzer = SourceCredibilityAnalyzer()
        score = await analyzer.analyze_url("http://example.com")
        assert score.ssl_info.has_ssl is False

    @pytest.mark.asyncio
    async def test_analyze_trusted_domain(self):
        """Test analyzing trusted domain."""
        analyzer = SourceCredibilityAnalyzer()
        score = await analyzer.analyze_url("https://bbc.com/news")
        assert score.credibility_score >= 70
        assert score.credibility_level in [
            SourceCredibility.CREDIBLE,
            SourceCredibility.HIGHLY_CREDIBLE
        ]

    @pytest.mark.asyncio
    async def test_analyze_edu_domain(self):
        """Test analyzing .edu domain."""
        analyzer = SourceCredibilityAnalyzer()
        score = await analyzer.analyze_url("https://mit.edu")
        assert score.credibility_score >= 50  # Should be credible
        assert "HTTPS" in score.trust_indicators or score.ssl_info.has_ssl

    @pytest.mark.asyncio
    async def test_analyze_new_domain(self):
        """Test analyzing newly registered domain."""
        analyzer = SourceCredibilityAnalyzer()
        score = await analyzer.analyze_url("https://example-new.com")
        # New domains should have lower scores
        assert score.credibility_score < 70

    @pytest.mark.asyncio
    async def test_analyze_typosquat_domain(self):
        """Test analyzing typosquat domain."""
        analyzer = SourceCredibilityAnalyzer()
        score = await analyzer.analyze_url("https://verify-account-update.com")
        # Typosquat domains should have lower credibility scores
        assert score.credibility_score < 70

    @pytest.mark.asyncio
    async def test_score_returns_valid_structure(self):
        """Test that returned score has valid structure."""
        analyzer = SourceCredibilityAnalyzer()
        score = await analyzer.analyze_url("https://example.com")
        assert hasattr(score, "domain")
        assert hasattr(score, "credibility_score")
        assert hasattr(score, "credibility_level")
        assert hasattr(score, "ssl_info")
        assert hasattr(score, "domain_info")
        assert hasattr(score, "reputation_score")
        assert hasattr(score, "trust_indicators")
        assert hasattr(score, "risk_indicators")
        assert hasattr(score, "summary")

    @pytest.mark.asyncio
    async def test_credibility_score_in_range(self):
        """Test that credibility score is 0-100."""
        analyzer = SourceCredibilityAnalyzer()
        urls = [
            "https://wikipedia.org",
            "https://unknown-site.xyz",
            "http://example.com"
        ]
        for url in urls:
            score = await analyzer.analyze_url(url)
            assert 0 <= score.credibility_score <= 100

    @pytest.mark.asyncio
    async def test_reputation_score_in_range(self):
        """Test that reputation score is 0-100."""
        analyzer = SourceCredibilityAnalyzer()
        score = await analyzer.analyze_url("https://example.com")
        assert 0 <= score.reputation_score <= 100

    def test_calculate_credibility_score_with_ssl(self):
        """Test score calculation with SSL."""
        ssl = SSLInfo(has_ssl=True, is_valid=True)
        domain = DomainInfo(domain="example.com", is_registered=True, age_years=5.0)
        
        score = SourceCredibilityAnalyzer._calculate_credibility_score(
            ssl, domain, 50, False
        )
        assert score >= 50  # Should get boost from SSL

    def test_calculate_credibility_score_without_ssl(self):
        """Test score calculation without SSL."""
        ssl = SSLInfo(has_ssl=False, is_valid=False)
        domain = DomainInfo(domain="example.com", is_registered=True, age_years=5.0)
        
        score = SourceCredibilityAnalyzer._calculate_credibility_score(
            ssl, domain, 50, False
        )
        assert score <= 50  # Should get penalty without SSL

    def test_determine_credibility_level_highly_credible(self):
        """Test credibility level determination - highly credible."""
        level = SourceCredibilityAnalyzer._determine_credibility_level(90)
        assert level == SourceCredibility.HIGHLY_CREDIBLE

    def test_determine_credibility_level_credible(self):
        """Test credibility level determination - credible."""
        level = SourceCredibilityAnalyzer._determine_credibility_level(75)
        assert level == SourceCredibility.CREDIBLE

    def test_determine_credibility_level_neutral(self):
        """Test credibility level determination - neutral."""
        level = SourceCredibilityAnalyzer._determine_credibility_level(55)
        assert level == SourceCredibility.NEUTRAL

    def test_determine_credibility_level_low(self):
        """Test credibility level determination - low."""
        level = SourceCredibilityAnalyzer._determine_credibility_level(35)
        assert level == SourceCredibility.LOW_CREDIBILITY

    def test_determine_credibility_level_suspicious(self):
        """Test credibility level determination - suspicious."""
        level = SourceCredibilityAnalyzer._determine_credibility_level(20)
        assert level == SourceCredibility.SUSPICIOUS


class TestGlobalInstances:
    """Tests for global singleton instances."""

    @pytest.mark.asyncio
    async def test_get_source_analyzer_singleton(self):
        """Test that get_source_analyzer returns same instance."""
        analyzer1 = get_source_analyzer()
        analyzer2 = get_source_analyzer()
        assert analyzer1 is analyzer2

    @pytest.mark.asyncio
    async def test_analyze_source_credibility_task(self):
        """Test async task wrapper."""
        result = await analyze_source_credibility("https://wikipedia.org")
        assert isinstance(result, dict)
        assert "domain" in result
        assert "credibility_score" in result
        assert "credibility_level" in result


class TestRealWorldScenarios:
    """Tests for real-world source credibility scenarios."""

    @pytest.mark.asyncio
    async def test_major_news_outlet(self):
        """Test analyzing major news outlets."""
        analyzer = SourceCredibilityAnalyzer()
        score = await analyzer.analyze_url("https://bbc.com/news")
        assert score.credibility_level in [
            SourceCredibility.CREDIBLE,
            SourceCredibility.HIGHLY_CREDIBLE
        ]

    @pytest.mark.asyncio
    async def test_government_domain(self):
        """Test analyzing government domains."""
        analyzer = SourceCredibilityAnalyzer()
        score = await analyzer.analyze_url("https://gov.uk")
        assert score.credibility_level in [
            SourceCredibility.CREDIBLE,
            SourceCredibility.HIGHLY_CREDIBLE
        ]

    @pytest.mark.asyncio
    async def test_educational_institution(self):
        """Test analyzing educational institutions."""
        analyzer = SourceCredibilityAnalyzer()
        score = await analyzer.analyze_url("https://mit.edu")
        assert score.credibility_level in [
            SourceCredibility.CREDIBLE,
            SourceCredibility.HIGHLY_CREDIBLE
        ]

    @pytest.mark.asyncio
    async def test_phishing_domain(self):
        """Test analyzing potential phishing domain."""
        analyzer = SourceCredibilityAnalyzer()
        score = await analyzer.analyze_url("https://verify-account-update.com")
        assert score.credibility_level in [
            SourceCredibility.LOW_CREDIBILITY,
            SourceCredibility.SUSPICIOUS
        ]
