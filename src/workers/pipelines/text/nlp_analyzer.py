"""NLP analysis for misinformation pattern detection and LLM-based analysis."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional
import warnings

from src.api.models.schemas import Verdict
from src.workers.pipelines.text.preprocessor import PreprocessedText

logger = logging.getLogger(__name__)


class MisinformationPattern(str, Enum):
    """Common misinformation patterns."""
    EMOTIONAL_LANGUAGE = "emotional_language"
    LOGICAL_FALLACY = "logical_fallacy"
    CLAIM_WITHOUT_SOURCE = "claim_without_source"
    SENSATIONALISM = "sensationalism"
    BIAS_LANGUAGE = "bias_language"
    UNVERIFIABLE_CLAIM = "unverifiable_claim"
    CONFLICTING_FACTS = "conflicting_facts"
    VAGUE_LANGUAGE = "vague_language"


@dataclass
class PatternMatch:
    """A detected misinformation pattern."""
    pattern: MisinformationPattern
    confidence: int  # 0-100
    text_span: str
    explanation: str
    start_pos: int
    end_pos: int

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class NLPFinding:
    """NLP analysis finding with verdict and confidence."""
    verdict: Verdict
    confidence: int  # 0-100
    summary: str
    patterns: list[PatternMatch]
    language_indicators: dict
    recommendation: str

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "verdict": self.verdict.value if isinstance(self.verdict, Verdict) else self.verdict,
            "confidence": self.confidence,
            "summary": self.summary,
            "patterns": [p.to_dict() for p in self.patterns],
            "language_indicators": self.language_indicators,
            "recommendation": self.recommendation,
        }


class PatternMatcher:
    """Pattern-based misinformation detection."""

    # Emotional language indicators
    EMOTIONAL_WORDS = {
        "shocking", "devastating", "outrageous", "unbelievable", "absolutely",
        "must read", "urgent", "exclusive", "breaking", "warning", "alert",
        "everybody should know", "they don't want you to know", "don't miss this",
        "incredible", "amazing", "horrifying", "disgusting", "terrible",
    }

    # Logical fallacy patterns
    LOGICAL_FALLACIES = {
        r"\ball\b.*\b(are|is|have|has)\b": "hasty_generalization",
        r"(because|since) [^.!?]{10,50}": "circular_reasoning",
        r"(obviously|clearly|undoubtedly) [^.!?]{10,80}": "appeal_to_authority",
        r"(if|assume) [^.!?]{5,50}\s+(then|therefore|so) [^.!?]{5,80}": "false_cause",
    }

    # Sensationalism patterns
    SENSATIONALISM = {
        r"!!!+": "excessive_punctuation",
        r"\b(MUST|SHOCKING|EXCLUSIVE|BREAKING|WARNING)\b": "caps_emphasis",
        r"\?\?+": "excessive_questions",
    }

    # Bias indicators
    BIAS_WORDS = {
        "only", "merely", "just", "simply", "nothing but",
        "obviously", "clearly", "undoubtedly", "of course",
        "alleged", "so-called", "purported",
    }

    # Vague language patterns
    VAGUE_WORDS = {
        "some", "many", "most", "lots", "several",
        "apparently", "reportedly", "supposedly", "allegedly",
        "might", "could", "may", "seems", "appears",
    }

    @staticmethod
    def find_emotional_language(text: str) -> list[PatternMatch]:
        """Detect emotional language."""
        matches = []
        text_lower = text.lower()
        words = text_lower.split()

        for word in PatternMatcher.EMOTIONAL_WORDS:
            if word in text_lower:
                pos = text_lower.find(word)
                matches.append(
                    PatternMatch(
                        pattern=MisinformationPattern.EMOTIONAL_LANGUAGE,
                        confidence=60,
                        text_span=word,
                        explanation=f"Emotional language detected: '{word}'",
                        start_pos=pos,
                        end_pos=pos + len(word),
                    )
                )

        return matches[:5]  # Limit to 5 matches

    @staticmethod
    def find_logical_fallacies(text: str) -> list[PatternMatch]:
        """Detect logical fallacies."""
        matches = []

        for pattern, fallacy_type in PatternMatcher.LOGICAL_FALLACIES.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                matches.append(
                    PatternMatch(
                        pattern=MisinformationPattern.LOGICAL_FALLACY,
                        confidence=70,
                        text_span=match.group(),
                        explanation=f"Potential {fallacy_type}",
                        start_pos=match.start(),
                        end_pos=match.end(),
                    )
                )

        return matches[:5]

    @staticmethod
    def find_sensationalism(text: str) -> list[PatternMatch]:
        """Detect sensationalism."""
        matches = []

        for pattern, sens_type in PatternMatcher.SENSATIONALISM.items():
            for match in re.finditer(pattern, text):
                matches.append(
                    PatternMatch(
                        pattern=MisinformationPattern.SENSATIONALISM,
                        confidence=50,
                        text_span=match.group(),
                        explanation=f"Sensationalism indicator: {sens_type}",
                        start_pos=match.start(),
                        end_pos=match.end(),
                    )
                )

        return matches[:5]

    @staticmethod
    def find_bias_language(text: str) -> list[PatternMatch]:
        """Detect biased language."""
        matches = []
        text_lower = text.lower()

        for word in PatternMatcher.BIAS_WORDS:
            if word in text_lower:
                pos = text_lower.find(word)
                matches.append(
                    PatternMatch(
                        pattern=MisinformationPattern.BIAS_LANGUAGE,
                        confidence=55,
                        text_span=word,
                        explanation=f"Potentially biased language: '{word}'",
                        start_pos=pos,
                        end_pos=pos + len(word),
                    )
                )

        return matches[:5]

    @staticmethod
    def find_vague_language(text: str) -> list[PatternMatch]:
        """Detect vague language."""
        matches = []
        text_lower = text.lower()

        for word in PatternMatcher.VAGUE_WORDS:
            if word in text_lower:
                pos = text_lower.find(word)
                matches.append(
                    PatternMatch(
                        pattern=MisinformationPattern.VAGUE_LANGUAGE,
                        confidence=45,
                        text_span=word,
                        explanation=f"Vague language detected: '{word}'",
                        start_pos=pos,
                        end_pos=pos + len(word),
                    )
                )

        return matches[:5]


class NLPAnalyzer:
    """Main NLP analyzer for misinformation detection."""

    def __init__(self):
        """Initialize the NLP analyzer."""
        self.pattern_matcher = PatternMatcher()

    async def analyze(self, text: str, timeout: int = 30) -> NLPFinding:
        """
        Analyze text for misinformation patterns using NLP.

        Args:
            text: Text to analyze
            timeout: Analysis timeout in seconds

        Returns:
            NLPFinding with verdict and patterns

        Raises:
            ValueError: If text is empty or None
            asyncio.TimeoutError: If analysis exceeds timeout
        """
        if not text or not text.strip():
            raise ValueError("Invalid text input: empty or None")

        if len(text) > 100000:
            logger.warning(f"Text length {len(text)} exceeds 100k, truncating")
            text = text[:100000]

        try:
            # Run analysis with timeout
            result = await asyncio.wait_for(
                self._perform_analysis(text),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            logger.error(f"NLP analysis timed out after {timeout}s")
            raise

    async def analyze_preprocessed(
        self,
        preprocessed_text: PreprocessedText,
        timeout: int = 30
    ) -> NLPFinding:
        """
        Analyze preprocessed text.

        Args:
            preprocessed_text: PreprocessedText object from preprocessor
            timeout: Analysis timeout in seconds

        Returns:
            NLPFinding with verdict and patterns
        """
        if not isinstance(preprocessed_text, PreprocessedText):
            raise ValueError("Expected PreprocessedText object")

        # Use cleaned text if available, otherwise use original
        text_to_analyze = preprocessed_text.cleaned_text or preprocessed_text.original_text
        return await self.analyze(text_to_analyze, timeout=timeout)

    async def _perform_analysis(self, text: str) -> NLPFinding:
        """Perform the actual NLP analysis."""
        patterns = []
        language_indicators = {}
        confidence_scores = []

        # Run pattern detection
        patterns.extend(self.pattern_matcher.find_emotional_language(text))
        patterns.extend(self.pattern_matcher.find_logical_fallacies(text))
        patterns.extend(self.pattern_matcher.find_sensationalism(text))
        patterns.extend(self.pattern_matcher.find_bias_language(text))
        patterns.extend(self.pattern_matcher.find_vague_language(text))

        # Collect language indicators
        if patterns:
            pattern_types = {}
            for pattern in patterns:
                pattern_name = pattern.pattern.value
                if pattern_name not in pattern_types:
                    pattern_types[pattern_name] = 0
                pattern_types[pattern_name] += 1
            language_indicators = pattern_types

        # Calculate confidence scores from patterns
        for pattern in patterns:
            confidence_scores.append(pattern.confidence)

        # Determine verdict based on patterns
        if not patterns:
            verdict = Verdict.SUPPORTED
            overall_confidence = 85
            summary = "No significant misinformation indicators detected."
            recommendation = "Content appears credible based on language analysis."
        elif len(patterns) >= 5:
            verdict = Verdict.DISPUTED
            overall_confidence = min(85, max(confidence_scores) if confidence_scores else 60)
            summary = f"Multiple misinformation indicators detected ({len(patterns)} patterns)."
            recommendation = "Content contains suspicious language patterns. Verify claims with authoritative sources."
        else:
            verdict = Verdict.UNVERIFIABLE
            overall_confidence = int(sum(confidence_scores) / len(confidence_scores)) if confidence_scores else 50
            summary = f"Some potential misinformation indicators ({len(patterns)} patterns)."
            recommendation = "Exercise caution. Cross-reference claims with reliable sources."

        return NLPFinding(
            verdict=verdict,
            confidence=overall_confidence,
            summary=summary,
            patterns=patterns,
            language_indicators=language_indicators,
            recommendation=recommendation,
        )


# Global singleton instance
_nlp_analyzer: Optional[NLPAnalyzer] = None


def get_nlp_analyzer() -> NLPAnalyzer:
    """Get or create the global NLP analyzer instance."""
    global _nlp_analyzer
    if _nlp_analyzer is None:
        _nlp_analyzer = NLPAnalyzer()
    return _nlp_analyzer


async def nlp_analysis_task(text: str, timeout: int = 30) -> dict:
    """
    Async task wrapper for NLP analysis.

    Args:
        text: Text to analyze
        timeout: Analysis timeout in seconds

    Returns:
        Dictionary representation of NLPFinding
    """
    analyzer = get_nlp_analyzer()
    finding = await analyzer.analyze(text, timeout=timeout)
    return finding.to_dict()
