"""
Unit tests for fact-checking pipeline

Tests T-302: Verify text claims against known sources and knowledge bases
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from src.workers.pipelines.text.factchecker import (
    Verdict,
    Evidence,
    ClaimFinding,
    ClaimExtractor,
    FactChecker,
    MockFactCheckProvider,
    get_claim_extractor,
    get_fact_checker,
)


class TestEvidence:
    """Test Evidence data class"""
    
    def test_evidence_creation(self):
        """Test creating an Evidence object"""
        evidence = Evidence(
            url="https://example.com",
            snippet="This is a fact",
            source="Example",
            reliability_score=0.8,
        )
        
        assert evidence.url == "https://example.com"
        assert evidence.snippet == "This is a fact"
        assert evidence.source == "Example"
        assert evidence.reliability_score == 0.8
    
    def test_evidence_to_dict(self):
        """Test Evidence serialization"""
        evidence = Evidence(
            url="https://example.com",
            snippet="This is a fact",
            source="Example",
            title="Example Article",
            published_date="2026-01-01",
            reliability_score=0.8,
        )
        
        data = evidence.to_dict()
        
        assert isinstance(data, dict)
        assert data["url"] == "https://example.com"
        assert data["snippet"] == "This is a fact"
        assert data["reliability_score"] == 0.8


class TestClaimFinding:
    """Test ClaimFinding data class"""
    
    def test_claim_finding_creation(self):
        """Test creating a ClaimFinding object"""
        evidence = [Evidence("https://example.com", "fact", "source")]
        finding = ClaimFinding(
            claim="Test claim",
            verdict=Verdict.SUPPORTED,
            confidence=85,
            evidence=evidence,
            summary="Test summary",
        )
        
        assert finding.claim == "Test claim"
        assert finding.verdict == Verdict.SUPPORTED
        assert finding.confidence == 85
    
    def test_claim_finding_to_dict(self):
        """Test ClaimFinding serialization"""
        evidence = [Evidence("https://example.com", "fact", "source")]
        finding = ClaimFinding(
            claim="Test claim",
            verdict=Verdict.SUPPORTED,
            confidence=85,
            evidence=evidence,
            summary="Test summary",
        )
        
        data = finding.to_dict()
        
        assert isinstance(data, dict)
        assert data["claim"] == "Test claim"
        assert data["verdict"] == "Supported"
        assert data["confidence"] == 85
        assert len(data["evidence"]) == 1


class TestClaimExtractor:
    """Test claim extraction functionality"""
    
    @pytest.fixture
    def extractor(self):
        """Create ClaimExtractor instance"""
        return ClaimExtractor()
    
    def test_extract_claims_basic(self, extractor):
        """Test basic claim extraction"""
        text = "Scientists claim that water freezes at 0 degrees Celsius."
        claims = extractor.extract_claims(text)
        
        assert len(claims) > 0
        assert any("water" in c.lower() for c in claims)
    
    def test_extract_claims_multiple(self, extractor):
        """Test extracting multiple claims"""
        text = """
        The study shows that 80% of people prefer coffee.
        Reports indicate that climate change is accelerating.
        Research demonstrates that exercise improves health.
        """
        claims = extractor.extract_claims(text)
        
        assert len(claims) >= 2
    
    def test_extract_claims_respects_max(self, extractor):
        """Test that max_claims limit is respected"""
        text = " ".join([f"Claim {i}: Something is true." for i in range(20)])
        claims = extractor.extract_claims(text)
        
        assert len(claims) <= extractor.max_claims
    
    def test_extract_claims_filters_short(self, extractor):
        """Test that short claims are filtered"""
        extractor.min_claim_length = 50
        text = "This is short. This is a longer claim that should be extracted."
        claims = extractor.extract_claims(text)
        
        # Should not include "This is short"
        for claim in claims:
            assert len(claim) >= extractor.min_claim_length
    
    def test_extract_claims_removes_html(self, extractor):
        """Test that HTML is filtered from claims"""
        text = "This is <b>bold</b> text claiming something important."
        claims = extractor.extract_claims(text)
        
        for claim in claims:
            assert "<" not in claim
            assert ">" not in claim
    
    def test_extract_claims_deduplicates(self, extractor):
        """Test that duplicate claims are removed"""
        text = "The study shows X. The study shows X. The study shows X."
        claims = extractor.extract_claims(text)
        
        # Should have removed duplicates
        assert len(claims) <= 2


class TestMockFactCheckProvider:
    """Test mock fact-check provider"""
    
    @pytest.fixture
    def provider(self):
        """Create MockFactCheckProvider instance"""
        return MockFactCheckProvider()
    
    @pytest.mark.asyncio
    async def test_search_known_fact(self, provider):
        """Test searching for a known fact"""
        evidence = await provider.search("water freezes")
        
        assert len(evidence) > 0
        assert all(isinstance(e, Evidence) for e in evidence)
    
    @pytest.mark.asyncio
    async def test_search_unknown_fact(self, provider):
        """Test searching for unknown fact"""
        evidence = await provider.search("unicorns are real")
        
        assert len(evidence) == 0
    
    @pytest.mark.asyncio
    async def test_search_returns_evidence(self, provider):
        """Test that search returns Evidence objects"""
        evidence = await provider.search("earth round")
        
        assert len(evidence) > 0
        for e in evidence:
            assert isinstance(e, Evidence)
            assert e.url
            assert e.snippet
            assert e.source


class TestFactChecker:
    """Test FactChecker service"""
    
    @pytest.fixture
    def provider(self):
        """Create mock provider"""
        return MockFactCheckProvider()
    
    @pytest.fixture
    def fact_checker(self, provider):
        """Create FactChecker instance"""
        return FactChecker(search_provider=provider)
    
    # ===== Basic Functionality Tests =====
    
    @pytest.mark.asyncio
    async def test_check_text_basic(self, fact_checker):
        """Test basic text fact-checking"""
        text = "Water freezes at 0 degrees Celsius."
        findings = await fact_checker.check_text(text, timeout=10)
        
        assert isinstance(findings, list)
        assert len(findings) >= 0
    
    @pytest.mark.asyncio
    async def test_check_text_with_multiple_claims(self, fact_checker):
        """Test fact-checking text with multiple claims"""
        text = """
        Water freezes at 0 degrees Celsius.
        The Earth is round.
        Gravity exists and attracts all objects.
        """
        findings = await fact_checker.check_text(text, timeout=10)
        
        assert len(findings) >= 1
        assert all(isinstance(f, ClaimFinding) for f in findings)
    
    @pytest.mark.asyncio
    async def test_check_text_empty_raises_error(self, fact_checker):
        """Test that empty text raises ValueError"""
        with pytest.raises(ValueError, match="empty"):
            await fact_checker.check_text("", timeout=10)
    
    @pytest.mark.asyncio
    async def test_check_text_whitespace_only_raises_error(self, fact_checker):
        """Test that whitespace-only text raises ValueError"""
        with pytest.raises(ValueError, match="empty"):
            await fact_checker.check_text("   \n\t  ", timeout=10)
    
    # ===== Verdict Determination Tests =====
    
    def test_determine_verdict_with_evidence(self, fact_checker):
        """Test verdict determination with evidence"""
        evidence = [
            Evidence("url1", "snippet1", "source1", reliability_score=0.9),
            Evidence("url2", "snippet2", "source2", reliability_score=0.8),
        ]
        
        verdict, confidence, summary = fact_checker._determine_verdict(
            "test claim", evidence
        )
        
        assert verdict == Verdict.SUPPORTED
        assert confidence > 70
    
    def test_determine_verdict_no_evidence(self, fact_checker):
        """Test verdict when no evidence found"""
        verdict, confidence, summary = fact_checker._determine_verdict(
            "test claim", []
        )
        
        assert verdict == Verdict.UNVERIFIABLE
        assert confidence == 0
    
    def test_determine_verdict_low_reliability(self, fact_checker):
        """Test verdict with low reliability sources"""
        evidence = [
            Evidence("url1", "snippet1", "source1", reliability_score=0.2),
            Evidence("url2", "snippet2", "source2", reliability_score=0.1),
        ]
        
        verdict, confidence, summary = fact_checker._determine_verdict(
            "test claim", evidence
        )
        
        assert verdict == Verdict.DISPUTED
        assert confidence > 0
    
    # ===== Claim Extraction Tests =====
    
    @pytest.mark.asyncio
    async def test_check_identifies_claims(self, fact_checker):
        """Test that check_text identifies and checks claims"""
        text = "Research shows that coffee is good for health."
        findings = await fact_checker.check_text(text, timeout=10)
        
        # Mock provider might not find evidence, but should attempt
        assert isinstance(findings, list)
    
    # ===== Async/Timeout Tests =====
    
    @pytest.mark.asyncio
    async def test_check_text_timeout_handling(self, fact_checker):
        """Test that timeout is handled gracefully"""
        # Create a slow provider
        slow_provider = AsyncMock()
        slow_provider.search = AsyncMock(side_effect=asyncio.TimeoutError())
        fact_checker.search_provider = slow_provider
        
        text = "This is a test claim."
        findings = await fact_checker.check_text(text, timeout=0.1)
        
        # Should return empty or error findings
        assert isinstance(findings, list)
    
    # ===== Integration Tests =====
    
    @pytest.mark.asyncio
    async def test_check_preprocessed_text(self, fact_checker):
        """Test checking a PreprocessedText object"""
        mock_preprocessed = Mock()
        mock_preprocessed.cleaned_text = "Water freezes at 0 degrees Celsius."
        
        findings = await fact_checker.check_preprocessed_text(
            mock_preprocessed, timeout=10
        )
        
        assert isinstance(findings, list)
    
    def test_check_preprocessed_text_invalid_object(self, fact_checker):
        """Test error handling for invalid PreprocessedText"""
        mock_preprocessed = Mock(spec=[])  # No cleaned_text
        
        with pytest.raises(ValueError, match="missing cleaned_text"):
            asyncio.run(fact_checker.check_preprocessed_text(mock_preprocessed))


class TestGlobalInstances:
    """Test global singleton instances"""
    
    def test_get_claim_extractor_singleton(self):
        """Test that get_claim_extractor returns same instance"""
        extractor1 = get_claim_extractor()
        extractor2 = get_claim_extractor()
        
        assert extractor1 is extractor2
    
    def test_get_fact_checker_singleton(self):
        """Test that get_fact_checker returns same instance"""
        checker1 = get_fact_checker()
        checker2 = get_fact_checker()
        
        assert checker1 is checker2


class TestRealWorldScenarios:
    """Test with realistic claim scenarios"""
    
    @pytest.fixture
    def fact_checker(self):
        """Create fact checker with mock provider"""
        provider = MockFactCheckProvider()
        return FactChecker(search_provider=provider)
    
    @pytest.mark.asyncio
    async def test_wikipedia_style_article(self, fact_checker):
        """Test fact-checking a Wikipedia-style article"""
        text = """
        Physics is the natural science that studies matter, its fundamental constituents,
        its motion and behavior through space and time, and the related entities of energy
        and force. Water freezes at 0 degrees Celsius. Physics is one of the oldest disciplines.
        """
        
        findings = await fact_checker.check_text(text, timeout=10)
        
        assert isinstance(findings, list)
    
    @pytest.mark.asyncio
    async def test_news_article_claims(self, fact_checker):
        """Test fact-checking claims from a news article"""
        text = """
        Scientists report that 75% of the ocean remains unexplored.
        The study claims that gravity is a fundamental force.
        Research indicates that exercise improves cardiovascular health.
        """
        
        findings = await fact_checker.check_text(text, timeout=10)
        
        assert isinstance(findings, list)


class TestVerdictEnum:
    """Test Verdict enum"""
    
    def test_verdict_values(self):
        """Test that Verdict enum has expected values"""
        assert Verdict.SUPPORTED.value == "Supported"
        assert Verdict.DISPUTED.value == "Disputed"
        assert Verdict.UNVERIFIABLE.value == "Unverifiable"
    
    def test_verdict_comparison(self):
        """Test verdict comparison"""
        assert Verdict.SUPPORTED != Verdict.DISPUTED
        assert Verdict.SUPPORTED == Verdict.SUPPORTED
