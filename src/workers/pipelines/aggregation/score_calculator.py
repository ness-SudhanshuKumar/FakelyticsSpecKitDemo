"""Overall credibility score calculation from aggregated findings."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class CredibilityLevel(str, Enum):
    """Overall credibility levels for content."""
    HIGHLY_CREDIBLE = "highly_credible"
    CREDIBLE = "credible"
    NEUTRAL = "neutral"
    LOW_CREDIBLE = "low_credible"
    NOT_CREDIBLE = "not_credible"


@dataclass
class ScoreComponent:
    """Individual component of credibility score."""
    name: str
    value: int  # 0-100
    weight: float  # 0.0-1.0
    explanation: str

    def weighted_score(self) -> float:
        """Calculate weighted score for this component."""
        return self.value * self.weight

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class CredibilityScoreResult:
    """Overall credibility score calculation result."""
    overall_score: int  # 0-100
    credibility_level: CredibilityLevel
    components: list[ScoreComponent]
    evidence_strength: int  # 0-100: How strong is evidence
    source_reliability: int  # 0-100: How reliable is the source
    content_quality: int  # 0-100: Overall content quality
    methodology: str  # Description of calculation methodology
    summary: str

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["credibility_level"] = self.credibility_level.value
        data["components"] = [c.to_dict() for c in self.components]
        return data


class CredibilityScoreCalculator:
    """Calculates overall credibility score from pipeline findings."""

    # Scoring algorithm configuration
    COMPONENT_WEIGHTS = {
        "text_verdict": 0.25,
        "text_confidence": 0.10,
        "spam_score": 0.15,  # Negative weight - lower spam = higher credibility
        "source_credibility": 0.25,
        "evidence_validation": 0.15,
        "consensus": 0.10,  # Agreement between pipelines
    }

    # Verdict scoring
    VERDICT_SCORES = {
        "Supported": 85,
        "supported": 85,
        "Credible": 80,
        "credible": 80,
        "Neutral": 50,
        "neutral": 50,
        "Disputed": 30,
        "disputed": 30,
        "Unverifiable": 50,
        "unverifiable": 50,
        "Low Credibility": 25,
        "low_credible": 25,
        "Suspicious": 20,
        "suspicious": 20,
        "Not Spam": 75,
        "not_spam": 75,
        "Suspicious (Spam)": 40,
        "likely_spam": 35,
        "Definite Spam": 10,
        "definite_spam": 10,
    }

    def __init__(self):
        """Initialize the calculator."""
        pass

    async def calculate_score(
        self,
        findings: dict,
        timeout: int = 30,
    ) -> CredibilityScoreResult:
        """
        Calculate overall credibility score from findings.

        Args:
            findings: Dictionary with pipeline findings:
                {
                    "text": {"verdict": "...", "confidence": ...},
                    "spam": {"verdict": "...", "score": ...},
                    "source": {"credibility_score": ..., "credibility_level": "..."},
                    "overall_verdict": "...",
                    "overall_confidence": ...
                }
            timeout: Calculation timeout in seconds

        Returns:
            CredibilityScoreResult with overall credibility score

        Raises:
            ValueError: If findings are invalid
        """
        if not findings or not isinstance(findings, dict):
            raise ValueError("Invalid findings: must be non-empty dict")

        try:
            result = await asyncio.wait_for(
                self._perform_calculation(findings),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Score calculation timed out after {timeout}s")
            raise

    async def _perform_calculation(self, findings: dict) -> CredibilityScoreResult:
        """Perform actual score calculation."""
        components = []

        # Extract findings from different pipelines
        text_verdict = findings.get("text", {}).get("verdict", "Unverifiable")
        text_confidence = findings.get("text", {}).get("confidence", 50)
        
        spam_verdict = findings.get("spam", {}).get("verdict", "Suspicious")
        spam_score = findings.get("spam", {}).get("spam_score", 50)
        
        source_credibility_level = findings.get("source", {}).get("credibility_level", "neutral")
        source_credibility_score = findings.get("source", {}).get("credibility_score", 50)
        
        evidence_validation_results = findings.get("evidence_validation", {})
        evidence_validation_score = evidence_validation_results.get("validation_score", 50)
        
        overall_verdict = findings.get("overall_verdict", "Unverifiable")
        overall_confidence = findings.get("overall_confidence", 50)

        # Calculate text verdict score
        text_verdict_score = self.VERDICT_SCORES.get(text_verdict, 50)
        components.append(ScoreComponent(
            name="Text Analysis Verdict",
            value=text_verdict_score,
            weight=self.COMPONENT_WEIGHTS["text_verdict"],
            explanation=f"Text analysis verdict: {text_verdict}"
        ))

        # Calculate text confidence component
        components.append(ScoreComponent(
            name="Text Analysis Confidence",
            value=text_confidence,
            weight=self.COMPONENT_WEIGHTS["text_confidence"],
            explanation=f"Text analysis confidence: {text_confidence}%"
        ))

        # Calculate spam score component (inverted: lower spam = higher credibility)
        # Spam score 0 = credible, 100 = not credible
        spam_credibility = 100 - spam_score
        components.append(ScoreComponent(
            name="Spam Detection Score",
            value=spam_credibility,
            weight=self.COMPONENT_WEIGHTS["spam_score"],
            explanation=f"Spam likelihood: {spam_score}% (lower is better)"
        ))

        # Calculate source credibility component
        components.append(ScoreComponent(
            name="Source Credibility",
            value=source_credibility_score,
            weight=self.COMPONENT_WEIGHTS["source_credibility"],
            explanation=f"Source credibility level: {source_credibility_level}"
        ))

        # Calculate evidence validation component
        components.append(ScoreComponent(
            name="Evidence Validation",
            value=evidence_validation_score,
            weight=self.COMPONENT_WEIGHTS["evidence_validation"],
            explanation="Evidence source validation and accessibility"
        ))

        # Calculate consensus component (from overall confidence)
        components.append(ScoreComponent(
            name="Pipeline Consensus",
            value=overall_confidence,
            weight=self.COMPONENT_WEIGHTS["consensus"],
            explanation=f"Agreement across multiple pipelines: {overall_confidence}%"
        ))

        # Calculate weighted overall score
        total_weighted_score = sum(c.weighted_score() for c in components)
        total_weight = sum(c.weight for c in components)
        overall_score = int(total_weighted_score / total_weight) if total_weight > 0 else 50

        # Ensure score is in valid range
        overall_score = max(0, min(100, overall_score))

        # Determine credibility level
        credibility_level = self._determine_credibility_level(overall_score)

        # Calculate sub-scores
        evidence_strength = max(0, min(100, evidence_validation_score))
        source_reliability = max(0, min(100, source_credibility_score))
        content_quality = max(0, min(100, text_verdict_score))

        # Generate summary
        summary = self._generate_summary(credibility_level, overall_score)

        return CredibilityScoreResult(
            overall_score=overall_score,
            credibility_level=credibility_level,
            components=components,
            evidence_strength=evidence_strength,
            source_reliability=source_reliability,
            content_quality=content_quality,
            methodology="Weighted aggregation of text analysis, spam detection, source credibility, evidence validation, and pipeline consensus",
            summary=summary,
        )

    @staticmethod
    def _determine_credibility_level(score: int) -> CredibilityLevel:
        """Determine credibility level from score."""
        if score >= 85:
            return CredibilityLevel.HIGHLY_CREDIBLE
        elif score >= 70:
            return CredibilityLevel.CREDIBLE
        elif score >= 50:
            return CredibilityLevel.NEUTRAL
        elif score >= 30:
            return CredibilityLevel.LOW_CREDIBLE
        else:
            return CredibilityLevel.NOT_CREDIBLE

    @staticmethod
    def _generate_summary(level: CredibilityLevel, score: int) -> str:
        """Generate human-readable summary."""
        level_text = {
            CredibilityLevel.HIGHLY_CREDIBLE: "highly credible",
            CredibilityLevel.CREDIBLE: "credible",
            CredibilityLevel.NEUTRAL: "neutral credibility",
            CredibilityLevel.LOW_CREDIBLE: "low credibility",
            CredibilityLevel.NOT_CREDIBLE: "not credible",
        }

        return f"Content has {level_text[level]} with overall score of {score}/100."


# Global singleton instance
_calculator: Optional[CredibilityScoreCalculator] = None


def get_score_calculator() -> CredibilityScoreCalculator:
    """Get or create the global score calculator instance."""
    global _calculator
    if _calculator is None:
        _calculator = CredibilityScoreCalculator()
    return _calculator


async def calculate_credibility_score(findings: dict, timeout: int = 30) -> dict:
    """
    Async task wrapper for credibility score calculation.

    Args:
        findings: Dictionary of findings from pipelines
        timeout: Calculation timeout in seconds

    Returns:
        Dictionary representation of CredibilityScoreResult
    """
    calculator = get_score_calculator()
    result = await calculator.calculate_score(findings, timeout=timeout)
    return result.to_dict()
