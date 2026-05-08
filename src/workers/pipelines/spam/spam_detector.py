"""Spam detection pipeline for identifying misinformation spread patterns."""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class SpamClassification(str, Enum):
    """Spam classification levels."""
    NOT_SPAM = "not_spam"
    SUSPICIOUS = "suspicious"
    LIKELY_SPAM = "likely_spam"
    DEFINITE_SPAM = "definite_spam"


@dataclass
class SpamIndicator:
    """Individual spam detection indicator."""
    indicator_type: str  # Pattern type (phishing, keyword_spam, etc)
    name: str  # Human-readable name
    matched_text: Optional[str]  # Text that matched
    confidence: int  # 0-100
    severity: str  # low, medium, high
    explanation: str

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SpamDetectionResult:
    """Overall spam detection assessment."""
    text: str
    is_spam: bool
    spam_classification: SpamClassification
    spam_score: int  # 0-100
    indicators: list[SpamIndicator]
    risk_level: str  # low, medium, high
    recommended_action: str
    summary: str

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "is_spam": self.is_spam,
            "spam_classification": self.spam_classification.value,
            "spam_score": self.spam_score,
            "indicators": [ind.to_dict() for ind in self.indicators],
            "risk_level": self.risk_level,
            "recommended_action": self.recommended_action,
            "summary": self.summary,
        }


class PatternDetector:
    """Detects spam patterns in text."""

    # Phishing patterns
    PHISHING_PATTERNS = {
        r"\bverify\b": "Account verification phishing",
        r"\bconfirm.*password\b": "Credential confirmation",
        r"\bupdate.*payment\b": "Update request phishing",
        r"\b(suspend|block|lock|disable).*account\b": "Account threat",
        r"\bclick.*here\b": "Urgent click bait",
    }

    # Keyword spam patterns
    KEYWORD_SPAM = {
        "free money": 60,
        "work from home": 50,
        "win prize": 70,
        "get rich quick": 75,
        "click here": 40,
        "limited time": 30,
        "act now": 30,
        "exclusive offer": 35,
        "no credit card required": 50,
    }

    # Common spam words
    SPAM_KEYWORDS = {
        "viagra": 80,
        "cialis": 80,
        "pharma": 70,
        "casino": 60,
        "poker": 50,
        "weight loss": 40,
        "cheap": 30,
        "discount": 20,
        "unsubscribe": 10,
    }

    # URL patterns that indicate spam
    URL_SPAM_PATTERNS = [
        r"bit\.ly",
        r"short\.link",
        r"tinyurl",
        r"goo\.gl",
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",  # IP address
    ]

    @staticmethod
    def find_phishing_patterns(text: str) -> list[SpamIndicator]:
        """Find phishing patterns in text."""
        indicators = []
        text_lower = text.lower()

        for pattern, description in PatternDetector.PHISHING_PATTERNS.items():
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                indicators.append(
                    SpamIndicator(
                        indicator_type="phishing",
                        name=description,
                        matched_text=match.group(0),
                        confidence=70,
                        severity="high",
                        explanation=f"Phishing-related language: {description}"
                    )
                )

        return indicators

    @staticmethod
    def find_keyword_spam(text: str) -> list[SpamIndicator]:
        """Find spam keyword patterns."""
        indicators = []
        text_lower = text.lower()

        for keyword, confidence in PatternDetector.KEYWORD_SPAM.items():
            if keyword in text_lower:
                count = text_lower.count(keyword)
                indicators.append(
                    SpamIndicator(
                        indicator_type="keyword_spam",
                        name=f"Spam keyword: {keyword}",
                        matched_text=keyword,
                        confidence=min(100, confidence + count * 5),
                        severity="medium" if confidence < 50 else "high",
                        explanation=f"Common spam keyword detected: '{keyword}'"
                    )
                )

        return indicators

    @staticmethod
    def find_spam_words(text: str) -> list[SpamIndicator]:
        """Find suspicious spam words."""
        indicators = []
        text_lower = text.lower()

        for word, confidence in PatternDetector.SPAM_KEYWORDS.items():
            if word in text_lower:
                indicators.append(
                    SpamIndicator(
                        indicator_type="spam_word",
                        name=f"Suspicious word: {word}",
                        matched_text=word,
                        confidence=confidence,
                        severity="medium" if confidence < 50 else "high",
                        explanation=f"Suspicious keyword associated with spam: '{word}'"
                    )
                )

        return indicators

    @staticmethod
    def find_url_spam_patterns(text: str) -> list[SpamIndicator]:
        """Find URL-based spam indicators."""
        indicators = []

        for pattern in PatternDetector.URL_SPAM_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                indicators.append(
                    SpamIndicator(
                        indicator_type="url_spam",
                        name="Suspicious URL pattern",
                        matched_text=match.group(0),
                        confidence=60,
                        severity="medium",
                        explanation=f"Suspicious URL pattern detected: {match.group(0)}"
                    )
                )

        return indicators

    @staticmethod
    def find_excessive_punctuation(text: str) -> list[SpamIndicator]:
        """Find excessive punctuation patterns."""
        indicators = []

        # Check for excessive exclamation marks
        exclamation_ratio = text.count("!") / max(len(text), 1)
        if exclamation_ratio > 0.05:  # More than 5% exclamation marks
            indicators.append(
                SpamIndicator(
                    indicator_type="excessive_punctuation",
                    name="Excessive exclamation marks",
                    matched_text="!!!",
                    confidence=40,
                    severity="low",
                    explanation="Text contains excessive exclamation marks"
                )
            )

        # Check for excessive caps
        caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
        if caps_ratio > 0.3:  # More than 30% uppercase
            indicators.append(
                SpamIndicator(
                    indicator_type="excessive_caps",
                    name="Excessive capitalization",
                    matched_text="CAPS",
                    confidence=35,
                    severity="low",
                    explanation="Text contains excessive capitalization"
                )
            )

        return indicators


class SpamDetector:
    """Main spam detection engine."""

    def __init__(self):
        """Initialize the detector."""
        self.detector = PatternDetector()

    async def detect_spam(self, text: str, timeout: int = 30) -> SpamDetectionResult:
        """
        Detect spam patterns in text.

        Args:
            text: Text to analyze for spam
            timeout: Detection timeout in seconds

        Returns:
            SpamDetectionResult with spam assessment

        Raises:
            ValueError: If text is invalid
        """
        if not text or not isinstance(text, str):
            raise ValueError("Invalid text: must be non-empty string")

        if len(text.strip()) == 0:
            raise ValueError("Invalid text: cannot be whitespace only")

        try:
            result = await asyncio.wait_for(
                self._perform_detection(text),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Spam detection timed out after {timeout}s")
            raise

    async def _perform_detection(self, text: str) -> SpamDetectionResult:
        """Perform actual spam detection."""
        # Collect all indicators
        indicators = []

        indicators.extend(self.detector.find_phishing_patterns(text))
        indicators.extend(self.detector.find_keyword_spam(text))
        indicators.extend(self.detector.find_spam_words(text))
        indicators.extend(self.detector.find_url_spam_patterns(text))
        indicators.extend(self.detector.find_excessive_punctuation(text))

        # Calculate spam score
        if not indicators:
            spam_score = 0
        else:
            # Average confidence of all indicators, weighted by severity
            severity_weights = {"low": 0.7, "medium": 1.0, "high": 1.3}
            weighted_sum = sum(
                ind.confidence * severity_weights.get(ind.severity, 1.0)
                for ind in indicators
            )
            total_weight = sum(
                severity_weights.get(ind.severity, 1.0)
                for ind in indicators
            )
            avg_score = weighted_sum / total_weight if total_weight > 0 else 0
            spam_score = int(min(100, avg_score * 1.1))  # Boost score slightly

        # Determine classification
        spam_classification = self._determine_classification(spam_score)
        # If we have phishing indicators, mark as spam regardless of base score
        has_phishing = any(ind.indicator_type == "phishing" for ind in indicators)
        is_spam = (spam_score >= 40) or has_phishing

        # Determine risk level
        risk_level = self._determine_risk_level(spam_score)

        # Generate recommendation
        recommended_action = self._generate_recommendation(spam_classification)

        # Generate summary
        summary = self._generate_summary(spam_classification, len(indicators))

        return SpamDetectionResult(
            text=text,
            is_spam=is_spam,
            spam_classification=spam_classification,
            spam_score=spam_score,
            indicators=indicators,
            risk_level=risk_level,
            recommended_action=recommended_action,
            summary=summary,
        )

    @staticmethod
    def _determine_classification(score: int) -> SpamClassification:
        """Determine spam classification from score."""
        if score >= 75:
            return SpamClassification.DEFINITE_SPAM
        elif score >= 60:
            return SpamClassification.LIKELY_SPAM
        elif score >= 40:
            return SpamClassification.SUSPICIOUS
        else:
            return SpamClassification.NOT_SPAM

    @staticmethod
    def _determine_risk_level(score: int) -> str:
        """Determine risk level from score."""
        if score >= 70:
            return "high"
        elif score >= 45:
            return "medium"
        else:
            return "low"

    @staticmethod
    def _generate_recommendation(classification: SpamClassification) -> str:
        """Generate action recommendation."""
        recommendations = {
            SpamClassification.DEFINITE_SPAM: "Flag as spam and block",
            SpamClassification.LIKELY_SPAM: "Quarantine for review",
            SpamClassification.SUSPICIOUS: "Review for manual verification",
            SpamClassification.NOT_SPAM: "Allow to proceed",
        }
        return recommendations.get(classification, "Unknown")

    @staticmethod
    def _generate_summary(classification: SpamClassification, indicator_count: int) -> str:
        """Generate human-readable summary."""
        level_text = {
            SpamClassification.NOT_SPAM: "not spam",
            SpamClassification.SUSPICIOUS: "suspicious",
            SpamClassification.LIKELY_SPAM: "likely spam",
            SpamClassification.DEFINITE_SPAM: "definitely spam",
        }

        return f"Content classified as {level_text[classification]} with {indicator_count} spam indicator(s) detected."


# Global singleton instance
_spam_detector: Optional[SpamDetector] = None


def get_spam_detector() -> SpamDetector:
    """Get or create the global spam detector instance."""
    global _spam_detector
    if _spam_detector is None:
        _spam_detector = SpamDetector()
    return _spam_detector


async def spam_detection_task(text: str, timeout: int = 30) -> dict:
    """
    Async task wrapper for spam detection.

    Args:
        text: Text to analyze
        timeout: Detection timeout in seconds

    Returns:
        Dictionary representation of SpamDetectionResult
    """
    detector = get_spam_detector()
    result = await detector.detect_spam(text, timeout=timeout)
    return result.to_dict()
