"""Unit tests for NLP analyzer module (T-303)."""

import asyncio
import pytest

from src.api.models.schemas import Verdict
from src.workers.pipelines.text.nlp_analyzer import (
    NLPAnalyzer,
    NLPFinding,
    PatternMatch,
    PatternMatcher,
    MisinformationPattern,
    get_nlp_analyzer,
    nlp_analysis_task,
)
from src.workers.pipelines.text.preprocessor import PreprocessedText, TextMetadata, Language


class TestPatternMatcher:
    """Tests for PatternMatcher class."""

    def test_find_emotional_language(self):
        """Test detection of emotional language."""
        text = "This is absolutely shocking and unbelievable!"
        matches = PatternMatcher.find_emotional_language(text)
        assert len(matches) > 0
        assert matches[0].pattern == MisinformationPattern.EMOTIONAL_LANGUAGE
        assert matches[0].confidence > 0

    def test_find_emotional_language_empty(self):
        """Test empty result for neutral text."""
        text = "The weather is mild today."
        matches = PatternMatcher.find_emotional_language(text)
        assert len(matches) == 0

    def test_find_logical_fallacies(self):
        """Test detection of logical fallacies."""
        text = "All politicians are liars because this one lied."
        matches = PatternMatcher.find_logical_fallacies(text)
        assert len(matches) > 0
        assert matches[0].pattern == MisinformationPattern.LOGICAL_FALLACY

    def test_find_sensationalism(self):
        """Test detection of sensationalism."""
        text = "BREAKING!!! EXCLUSIVE NEWS!!!"
        matches = PatternMatcher.find_sensationalism(text)
        assert len(matches) > 0
        assert matches[0].pattern == MisinformationPattern.SENSATIONALISM

    def test_find_bias_language(self):
        """Test detection of biased language."""
        text = "Obviously, this is clearly the only way to see it."
        matches = PatternMatcher.find_bias_language(text)
        assert len(matches) > 0
        assert matches[0].pattern == MisinformationPattern.BIAS_LANGUAGE

    def test_find_vague_language(self):
        """Test detection of vague language."""
        text = "Many people allegedly say that something might be true."
        matches = PatternMatcher.find_vague_language(text)
        assert len(matches) > 0
        assert matches[0].pattern == MisinformationPattern.VAGUE_LANGUAGE


class TestPatternMatch:
    """Tests for PatternMatch dataclass."""

    def test_pattern_match_creation(self):
        """Test creating a PatternMatch."""
        match = PatternMatch(
            pattern=MisinformationPattern.EMOTIONAL_LANGUAGE,
            confidence=70,
            text_span="shocking",
            explanation="Emotional word detected",
            start_pos=0,
            end_pos=8,
        )
        assert match.pattern == MisinformationPattern.EMOTIONAL_LANGUAGE
        assert match.confidence == 70

    def test_pattern_match_to_dict(self):
        """Test converting PatternMatch to dict."""
        match = PatternMatch(
            pattern=MisinformationPattern.LOGICAL_FALLACY,
            confidence=75,
            text_span="all are",
            explanation="Hasty generalization",
            start_pos=5,
            end_pos=12,
        )
        d = match.to_dict()
        assert d["pattern"] == "logical_fallacy"
        assert d["confidence"] == 75
        assert d["text_span"] == "all are"


class TestNLPFinding:
    """Tests for NLPFinding dataclass."""

    def test_nlp_finding_creation(self):
        """Test creating an NLPFinding."""
        finding = NLPFinding(
            verdict=Verdict.DISPUTED,
            confidence=75,
            summary="Text contains misinformation indicators",
            patterns=[],
            language_indicators={},
            recommendation="Verify with sources",
        )
        assert finding.verdict == Verdict.DISPUTED
        assert finding.confidence == 75

    def test_nlp_finding_to_dict(self):
        """Test converting NLPFinding to dict."""
        finding = NLPFinding(
            verdict=Verdict.SUPPORTED,
            confidence=85,
            summary="Content is credible",
            patterns=[],
            language_indicators={"emotional_language": 1},
            recommendation="No action needed",
        )
        d = finding.to_dict()
        assert d["verdict"] == "Supported"
        assert d["confidence"] == 85
        assert "language_indicators" in d


class TestNLPAnalyzer:
    """Tests for NLPAnalyzer class."""

    @pytest.mark.asyncio
    async def test_analyze_empty_text_raises_error(self):
        """Test that empty text raises ValueError."""
        analyzer = NLPAnalyzer()
        with pytest.raises(ValueError, match="Invalid text input"):
            await analyzer.analyze("")

    @pytest.mark.asyncio
    async def test_analyze_none_text_raises_error(self):
        """Test that None text raises ValueError."""
        analyzer = NLPAnalyzer()
        with pytest.raises(ValueError, match="Invalid text input"):
            await analyzer.analyze(None)

    @pytest.mark.asyncio
    async def test_analyze_whitespace_only_raises_error(self):
        """Test that whitespace-only text raises ValueError."""
        analyzer = NLPAnalyzer()
        with pytest.raises(ValueError, match="Invalid text input"):
            await analyzer.analyze("   \n\t  ")

    @pytest.mark.asyncio
    async def test_analyze_neutral_text_returns_supported(self):
        """Test analyzing neutral text returns high confidence verdict."""
        analyzer = NLPAnalyzer()
        text = "The weather today is mild with some clouds."
        finding = await analyzer.analyze(text)
        # Neutral text should have low pattern count and high confidence
        assert finding.verdict in [Verdict.SUPPORTED, Verdict.UNVERIFIABLE]
        assert finding.confidence >= 0
        assert finding.confidence <= 100
        assert finding.confidence >= 70 or len(finding.patterns) > 0

    @pytest.mark.asyncio
    async def test_analyze_misinformation_text_returns_disputed(self):
        """Test analyzing text with misinformation patterns."""
        analyzer = NLPAnalyzer()
        text = "This is absolutely shocking and unbelievable! All experts are lying because obviously they want to hide the truth."
        finding = await analyzer.analyze(text)
        assert finding.verdict == Verdict.DISPUTED
        assert len(finding.patterns) > 0

    @pytest.mark.asyncio
    async def test_analyze_returns_nlp_finding(self):
        """Test that analyze returns an NLPFinding."""
        analyzer = NLPAnalyzer()
        text = "Sample text for analysis"
        finding = await analyzer.analyze(text)
        assert isinstance(finding, NLPFinding)
        assert hasattr(finding, "verdict")
        assert hasattr(finding, "confidence")
        assert hasattr(finding, "patterns")
        assert hasattr(finding, "summary")

    @pytest.mark.asyncio
    async def test_analyze_with_timeout(self):
        """Test analyze with custom timeout."""
        analyzer = NLPAnalyzer()
        text = "Quick text"
        finding = await analyzer.analyze(text, timeout=10)
        assert isinstance(finding, NLPFinding)

    @pytest.mark.asyncio
    async def test_analyze_preprocessed_text(self):
        """Test analyzing preprocessed text object."""
        analyzer = NLPAnalyzer()
        preprocessed = PreprocessedText(
            original_text="The weather is nice",
            cleaned_text="weather nice",
            sentences=["The weather is nice"],
            tokens=["the", "weather", "is", "nice"],
            metadata=TextMetadata(
                original_length=19,
                cleaned_length=12,
                languages=["en"],
                detected_language="en",
                num_sentences=1,
                num_tokens=4,
                has_urls=False,
                has_emails=False,
                avg_word_length=5.0,
            ),
        )
        finding = await analyzer.analyze_preprocessed(preprocessed)
        assert isinstance(finding, NLPFinding)
        assert finding.verdict in [Verdict.SUPPORTED, Verdict.DISPUTED, Verdict.UNVERIFIABLE]

    @pytest.mark.asyncio
    async def test_analyze_preprocessed_invalid_object_raises_error(self):
        """Test that invalid object raises ValueError."""
        analyzer = NLPAnalyzer()
        with pytest.raises(ValueError, match="Expected PreprocessedText"):
            await analyzer.analyze_preprocessed("not a preprocessed object")

    @pytest.mark.asyncio
    async def test_analyze_truncates_very_long_text(self):
        """Test that very long text is truncated."""
        analyzer = NLPAnalyzer()
        text = "word " * 50000  # Create very long text
        finding = await analyzer.analyze(text)
        assert isinstance(finding, NLPFinding)

    @pytest.mark.asyncio
    async def test_analyze_verdict_consistency(self):
        """Test that verdicts are consistent Verdict enums."""
        analyzer = NLPAnalyzer()
        texts = [
            "Normal text about weather",
            "This is SHOCKING and BREAKING NEWS!!!",
            "Allegedly, someone might have possibly done something",
        ]
        for text in texts:
            finding = await analyzer.analyze(text)
            assert finding.verdict in [Verdict.SUPPORTED, Verdict.DISPUTED, Verdict.UNVERIFIABLE]

    @pytest.mark.asyncio
    async def test_analyze_confidence_in_range(self):
        """Test that confidence is always between 0-100."""
        analyzer = NLPAnalyzer()
        texts = [
            "Simple text",
            "BREAKING: SHOCKING NEWS!!!",
            "Obviously, clearly, undoubtedly this is true",
        ]
        for text in texts:
            finding = await analyzer.analyze(text)
            assert 0 <= finding.confidence <= 100

    @pytest.mark.asyncio
    async def test_pattern_match_positions(self):
        """Test that pattern matches have valid positions."""
        analyzer = NLPAnalyzer()
        text = "This is absolutely shocking!"
        finding = await analyzer.analyze(text)
        for pattern in finding.patterns:
            assert pattern.start_pos >= 0
            assert pattern.end_pos > pattern.start_pos
            assert pattern.end_pos <= len(text)


class TestGlobalInstances:
    """Tests for global singleton instances."""

    def test_get_nlp_analyzer_singleton(self):
        """Test that get_nlp_analyzer returns same instance."""
        analyzer1 = get_nlp_analyzer()
        analyzer2 = get_nlp_analyzer()
        assert analyzer1 is analyzer2

    @pytest.mark.asyncio
    async def test_nlp_analysis_task(self):
        """Test async task wrapper."""
        text = "Sample text for analysis"
        result = await nlp_analysis_task(text)
        assert isinstance(result, dict)
        assert "verdict" in result
        assert "confidence" in result
        assert "patterns" in result


class TestRealWorldScenarios:
    """Tests for real-world misinformation scenarios."""

    @pytest.mark.asyncio
    async def test_conspiracy_theory_text(self):
        """Test analyzing conspiracy theory text."""
        analyzer = NLPAnalyzer()
        text = (
            "BREAKING NEWS!!! Shocking evidence shows that THEY don't want you to know "
            "the truth! Obviously this proves that all media is lying because "
            "some sources might have been incorrect. Everyone should read this EXCLUSIVE report!"
        )
        finding = await analyzer.analyze(text)
        assert finding.verdict == Verdict.DISPUTED
        assert len(finding.patterns) > 0
        assert finding.confidence > 50

    @pytest.mark.asyncio
    async def test_balanced_news_article(self):
        """Test analyzing balanced news article."""
        analyzer = NLPAnalyzer()
        text = (
            "A new study suggests that certain climate patterns may be linked to human activity. "
            "The research, published in peer-reviewed journals, shows statistical correlation "
            "between emissions and temperature changes. However, some scientists argue that "
            "additional research is needed before drawing firm conclusions."
        )
        finding = await analyzer.analyze(text)
        assert finding.verdict in [Verdict.SUPPORTED, Verdict.UNVERIFIABLE]

    @pytest.mark.asyncio
    async def test_neutral_factual_text(self):
        """Test analyzing neutral, factual text."""
        analyzer = NLPAnalyzer()
        text = (
            "Paris is the capital of France. The city is located in the north-central part of the country "
            "on the Seine river. France has a population of approximately 67 million people. "
            "Paris is known for its architecture and cultural significance."
        )
        finding = await analyzer.analyze(text)
        assert finding.verdict == Verdict.SUPPORTED
        assert finding.confidence >= 70

    @pytest.mark.asyncio
    async def test_mixed_quality_text(self):
        """Test analyzing text with mixed quality indicators."""
        analyzer = NLPAnalyzer()
        text = (
            "According to reports, the company allegedly improved its performance. "
            "Some analysts suggest it might be due to the new strategy, though others say "
            "it could be market conditions. The data clearly shows growth in several areas."
        )
        finding = await analyzer.analyze(text)
        # Mixed text with vague language and some bias should be disputed or unverifiable
        assert finding.verdict in [Verdict.UNVERIFIABLE, Verdict.DISPUTED]
        assert len(finding.patterns) > 0
