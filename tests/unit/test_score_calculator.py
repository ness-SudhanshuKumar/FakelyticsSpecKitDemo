"""Unit tests for credibility score calculator module (T-702)."""

import pytest

from src.workers.pipelines.aggregation.score_calculator import (
    CredibilityLevel,
    ScoreComponent,
    CredibilityScoreResult,
    CredibilityScoreCalculator,
    get_score_calculator,
    calculate_credibility_score,
)


class TestScoreComponent:
    """Tests for ScoreComponent dataclass."""

    def test_score_component_creation(self):
        """Test creating score component."""
        component = ScoreComponent(
            name="Text Verdict",
            value=80,
            weight=0.25,
            explanation="Text analysis score"
        )
        assert component.value == 80
        assert component.weight == 0.25

    def test_score_component_weighted_score(self):
        """Test calculating weighted score."""
        component = ScoreComponent(
            name="Test",
            value=100,
            weight=0.5,
            explanation="Test component"
        )
        assert component.weighted_score() == 50.0

    def test_score_component_to_dict(self):
        """Test converting component to dict."""
        component = ScoreComponent(
            name="Source Credibility",
            value=75,
            weight=0.3,
            explanation="Source analysis"
        )
        d = component.to_dict()
        assert d["name"] == "Source Credibility"
        assert d["value"] == 75


class TestCredibilityScoreResult:
    """Tests for CredibilityScoreResult dataclass."""

    def test_result_creation(self):
        """Test creating score result."""
        result = CredibilityScoreResult(
            overall_score=75,
            credibility_level=CredibilityLevel.CREDIBLE,
            components=[],
            evidence_strength=80,
            source_reliability=70,
            content_quality=75,
            methodology="Test methodology",
            summary="Test summary"
        )
        assert result.overall_score == 75
        assert result.credibility_level == CredibilityLevel.CREDIBLE

    def test_result_to_dict(self):
        """Test converting result to dict."""
        result = CredibilityScoreResult(
            overall_score=85,
            credibility_level=CredibilityLevel.HIGHLY_CREDIBLE,
            components=[],
            evidence_strength=90,
            source_reliability=85,
            content_quality=80,
            methodology="Test",
            summary="Highly credible content"
        )
        d = result.to_dict()
        assert d["credibility_level"] == "highly_credible"
        assert d["overall_score"] == 85


class TestCredibilityScoreCalculator:
    """Tests for CredibilityScoreCalculator class."""

    @pytest.mark.asyncio
    async def test_calculate_empty_findings_raises_error(self):
        """Test that empty findings raises ValueError."""
        calculator = CredibilityScoreCalculator()
        with pytest.raises(ValueError, match="Invalid findings"):
            await calculator.calculate_score({})

    @pytest.mark.asyncio
    async def test_calculate_none_findings_raises_error(self):
        """Test that None findings raises ValueError."""
        calculator = CredibilityScoreCalculator()
        with pytest.raises(ValueError, match="Invalid findings"):
            await calculator.calculate_score(None)

    @pytest.mark.asyncio
    async def test_calculate_minimal_findings(self):
        """Test calculating with minimal findings."""
        calculator = CredibilityScoreCalculator()
        findings = {
            "text": {"verdict": "Supported", "confidence": 80},
            "spam": {"verdict": "Not Spam", "spam_score": 10},
            "source": {"credibility_score": 75, "credibility_level": "credible"},
            "evidence_validation": {"validation_score": 80},
            "overall_verdict": "Supported",
            "overall_confidence": 80,
        }
        result = await calculator.calculate_score(findings)
        assert isinstance(result, CredibilityScoreResult)
        assert 0 <= result.overall_score <= 100

    @pytest.mark.asyncio
    async def test_calculate_highly_credible_content(self):
        """Test calculating score for highly credible content."""
        calculator = CredibilityScoreCalculator()
        findings = {
            "text": {"verdict": "Supported", "confidence": 95},
            "spam": {"verdict": "Not Spam", "spam_score": 5},
            "source": {"credibility_score": 95, "credibility_level": "highly_credible"},
            "evidence_validation": {"validation_score": 90},
            "overall_verdict": "Supported",
            "overall_confidence": 90,
        }
        result = await calculator.calculate_score(findings)
        assert result.overall_score >= 80
        assert result.credibility_level == CredibilityLevel.HIGHLY_CREDIBLE

    @pytest.mark.asyncio
    async def test_calculate_low_credible_content(self):
        """Test calculating score for low credibility content."""
        calculator = CredibilityScoreCalculator()
        findings = {
            "text": {"verdict": "Disputed", "confidence": 40},
            "spam": {"verdict": "Likely Spam", "spam_score": 70},
            "source": {"credibility_score": 30, "credibility_level": "low_credible"},
            "evidence_validation": {"validation_score": 25},
            "overall_verdict": "Disputed",
            "overall_confidence": 40,
        }
        result = await calculator.calculate_score(findings)
        assert result.overall_score <= 50
        assert result.credibility_level in [
            CredibilityLevel.LOW_CREDIBLE,
            CredibilityLevel.NEUTRAL
        ]

    @pytest.mark.asyncio
    async def test_calculate_returns_valid_structure(self):
        """Test that result has valid structure."""
        calculator = CredibilityScoreCalculator()
        findings = {
            "text": {"verdict": "Unverifiable", "confidence": 50},
            "spam": {"verdict": "Suspicious", "spam_score": 50},
            "source": {"credibility_score": 50, "credibility_level": "neutral"},
            "evidence_validation": {"validation_score": 50},
            "overall_verdict": "Unverifiable",
            "overall_confidence": 50,
        }
        result = await calculator.calculate_score(findings)
        assert hasattr(result, "overall_score")
        assert hasattr(result, "credibility_level")
        assert hasattr(result, "components")
        assert hasattr(result, "evidence_strength")
        assert hasattr(result, "source_reliability")
        assert hasattr(result, "content_quality")
        assert hasattr(result, "methodology")
        assert hasattr(result, "summary")

    @pytest.mark.asyncio
    async def test_components_have_weights(self):
        """Test that components have proper weights."""
        calculator = CredibilityScoreCalculator()
        findings = {
            "text": {"verdict": "Supported", "confidence": 80},
            "spam": {"verdict": "Not Spam", "spam_score": 10},
            "source": {"credibility_score": 80, "credibility_level": "credible"},
            "evidence_validation": {"validation_score": 85},
            "overall_verdict": "Supported",
            "overall_confidence": 80,
        }
        result = await calculator.calculate_score(findings)
        # Check that all components have weights that sum to 1.0
        total_weight = sum(c.weight for c in result.components)
        assert abs(total_weight - 1.0) < 0.01

    def test_determine_credibility_level_highly_credible(self):
        """Test credibility level - highly credible."""
        level = CredibilityScoreCalculator._determine_credibility_level(90)
        assert level == CredibilityLevel.HIGHLY_CREDIBLE

    def test_determine_credibility_level_credible(self):
        """Test credibility level - credible."""
        level = CredibilityScoreCalculator._determine_credibility_level(75)
        assert level == CredibilityLevel.CREDIBLE

    def test_determine_credibility_level_neutral(self):
        """Test credibility level - neutral."""
        level = CredibilityScoreCalculator._determine_credibility_level(55)
        assert level == CredibilityLevel.NEUTRAL

    def test_determine_credibility_level_low(self):
        """Test credibility level - low credible."""
        level = CredibilityScoreCalculator._determine_credibility_level(35)
        assert level == CredibilityLevel.LOW_CREDIBLE

    def test_determine_credibility_level_not_credible(self):
        """Test credibility level - not credible."""
        level = CredibilityScoreCalculator._determine_credibility_level(15)
        assert level == CredibilityLevel.NOT_CREDIBLE


class TestGlobalInstances:
    """Tests for global singleton instances."""

    @pytest.mark.asyncio
    async def test_get_score_calculator_singleton(self):
        """Test that get_score_calculator returns same instance."""
        calc1 = get_score_calculator()
        calc2 = get_score_calculator()
        assert calc1 is calc2

    @pytest.mark.asyncio
    async def test_calculate_credibility_score_task(self):
        """Test async task wrapper."""
        findings = {
            "text": {"verdict": "Supported", "confidence": 85},
            "spam": {"verdict": "Not Spam", "spam_score": 10},
            "source": {"credibility_score": 80, "credibility_level": "credible"},
            "evidence_validation": {"validation_score": 85},
            "overall_verdict": "Supported",
            "overall_confidence": 80,
        }
        result_dict = await calculate_credibility_score(findings)
        assert isinstance(result_dict, dict)
        assert "overall_score" in result_dict
        assert "credibility_level" in result_dict


class TestRealWorldScenarios:
    """Tests for real-world scoring scenarios."""

    @pytest.mark.asyncio
    async def test_wikipedia_article_scoring(self):
        """Test scoring Wikipedia article."""
        calculator = CredibilityScoreCalculator()
        findings = {
            "text": {"verdict": "Supported", "confidence": 85},
            "spam": {"verdict": "Not Spam", "spam_score": 5},
            "source": {"credibility_score": 95, "credibility_level": "highly_credible"},
            "evidence_validation": {"validation_score": 90},
            "overall_verdict": "Supported",
            "overall_confidence": 88,
        }
        result = await calculator.calculate_score(findings)
        assert result.overall_score >= 80
        assert result.credibility_level in [
            CredibilityLevel.HIGHLY_CREDIBLE,
            CredibilityLevel.CREDIBLE
        ]

    @pytest.mark.asyncio
    async def test_misinformation_scoring(self):
        """Test scoring obvious misinformation."""
        calculator = CredibilityScoreCalculator()
        findings = {
            "text": {"verdict": "Disputed", "confidence": 85},
            "spam": {"verdict": "Likely Spam", "spam_score": 75},
            "source": {"credibility_score": 20, "credibility_level": "suspicious"},
            "evidence_validation": {"validation_score": 15},
            "overall_verdict": "Disputed",
            "overall_confidence": 80,
        }
        result = await calculator.calculate_score(findings)
        assert result.overall_score <= 40
        assert result.credibility_level in [
            CredibilityLevel.LOW_CREDIBLE,
            CredibilityLevel.NOT_CREDIBLE
        ]

    @pytest.mark.asyncio
    async def test_neutral_content_scoring(self):
        """Test scoring neutral/unverifiable content."""
        calculator = CredibilityScoreCalculator()
        findings = {
            "text": {"verdict": "Unverifiable", "confidence": 50},
            "spam": {"verdict": "Suspicious", "spam_score": 50},
            "source": {"credibility_score": 60, "credibility_level": "neutral"},
            "evidence_validation": {"validation_score": 50},
            "overall_verdict": "Unverifiable",
            "overall_confidence": 50,
        }
        result = await calculator.calculate_score(findings)
        assert 40 <= result.overall_score <= 65
        assert result.credibility_level in [
            CredibilityLevel.NEUTRAL,
            CredibilityLevel.LOW_CREDIBLE
        ]

    @pytest.mark.asyncio
    async def test_mixed_pipeline_results(self):
        """Test scoring with mixed results from pipelines."""
        calculator = CredibilityScoreCalculator()
        findings = {
            "text": {"verdict": "Supported", "confidence": 70},
            "spam": {"verdict": "Not Spam", "spam_score": 20},
            "source": {"credibility_score": 65, "credibility_level": "credible"},
            "evidence_validation": {"validation_score": 75},
            "overall_verdict": "Supported",
            "overall_confidence": 70,
        }
        result = await calculator.calculate_score(findings)
        assert result.overall_score >= 50
        assert result.credibility_level in [
            CredibilityLevel.CREDIBLE,
            CredibilityLevel.NEUTRAL
        ]
