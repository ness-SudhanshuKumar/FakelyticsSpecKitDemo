"""Finding aggregation service that combines results from all verification pipelines."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class OverallVerdict(str, Enum):
    """Overall verdict classification."""
    SUPPORTED = "supported"
    DISPUTED = "disputed"
    UNVERIFIABLE = "unverifiable"
    MIXED = "mixed"


@dataclass
class PipelineResult:
    """Result from a single verification pipeline."""
    pipeline_name: str  # "text", "image", "audio_video", "spam", "source"
    verdict: str  # "Supported", "Disputed", "Unverifiable"
    confidence: int  # 0-100
    score: Optional[int] = None  # Pipeline-specific score
    indicators_count: int = 0  # Number of indicators/findings
    summary: str = ""
    error: Optional[str] = None  # Error if pipeline failed

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class AggregatedFinding:
    """Aggregated finding from all pipelines."""
    finding_id: str  # Unique identifier
    finding_type: str  # "text", "source", "spam", "pattern", etc.
    verdict: OverallVerdict
    confidence: int  # Overall confidence 0-100
    summary: str
    source_pipelines: list[str]  # Which pipelines contributed
    pipeline_results: list[PipelineResult] = field(default_factory=list)
    supporting_evidence: list[str] = field(default_factory=list)
    conflicting_evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["verdict"] = self.verdict.value
        data["pipeline_results"] = [pr.to_dict() for pr in self.pipeline_results]
        return data


@dataclass
class AggregationReport:
    """Complete aggregated report from all pipelines."""
    request_id: str
    url: str
    overall_verdict: OverallVerdict
    overall_confidence: int  # 0-100
    findings: list[AggregatedFinding]
    pipeline_statuses: dict[str, str]  # Map of pipeline -> status
    summary: str
    confidence_distribution: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = asdict(self)
        data["overall_verdict"] = self.overall_verdict.value
        data["findings"] = [f.to_dict() for f in self.findings]
        return data


class FindingAggregator:
    """Aggregates findings from multiple verification pipelines."""

    # Pipeline weights for scoring
    PIPELINE_WEIGHTS = {
        "text": 0.25,
        "image": 0.20,
        "audio_video": 0.20,
        "spam": 0.20,
        "source": 0.15,
    }

    def __init__(self):
        """Initialize the aggregator."""
        pass

    async def aggregate_findings(
        self,
        request_id: str,
        url: str,
        pipeline_results: dict[str, PipelineResult],
        timeout: int = 30,
    ) -> AggregationReport:
        """
        Aggregate findings from multiple pipelines.

        Args:
            request_id: Unique request identifier
            url: The URL being analyzed
            pipeline_results: Dict mapping pipeline name to PipelineResult
            timeout: Aggregation timeout in seconds

        Returns:
            AggregationReport with aggregated findings and overall verdict

        Raises:
            ValueError: If inputs are invalid
        """
        if not request_id or not isinstance(request_id, str):
            raise ValueError("Invalid request_id: must be non-empty string")

        if not url or not isinstance(url, str):
            raise ValueError("Invalid url: must be non-empty string")

        if not pipeline_results or not isinstance(pipeline_results, dict):
            raise ValueError("Invalid pipeline_results: must be non-empty dict")

        try:
            result = await asyncio.wait_for(
                self._perform_aggregation(request_id, url, pipeline_results),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Aggregation timed out after {timeout}s")
            raise

    async def _perform_aggregation(
        self,
        request_id: str,
        url: str,
        pipeline_results: dict[str, PipelineResult],
    ) -> AggregationReport:
        """Perform actual aggregation."""
        # Process pipeline results
        aggregated_findings = []
        pipeline_statuses = {}
        verdicts = []
        confidences = []

        for pipeline_name, result in pipeline_results.items():
            pipeline_statuses[pipeline_name] = "completed" if not result.error else "error"

            if result.error:
                logger.warning(f"Pipeline {pipeline_name} failed: {result.error}")
                continue

            # Track verdict and confidence
            verdicts.append(result.verdict)
            confidences.append(result.confidence)

            # Create aggregated finding
            finding = AggregatedFinding(
                finding_id=f"{request_id}_{pipeline_name}",
                finding_type=pipeline_name,
                verdict=self._normalize_verdict(result.verdict),
                confidence=result.confidence,
                summary=result.summary,
                source_pipelines=[pipeline_name],
                pipeline_results=[result],
            )
            aggregated_findings.append(finding)

        # Calculate overall verdict and confidence
        if not verdicts:
            overall_verdict = OverallVerdict.UNVERIFIABLE
            overall_confidence = 0
        else:
            overall_verdict = self._calculate_overall_verdict(verdicts, confidences)
            overall_confidence = self._calculate_overall_confidence(confidences)

        # Generate summary
        summary = self._generate_summary(overall_verdict, len(aggregated_findings))

        # Calculate confidence distribution
        confidence_dist = self._calculate_confidence_distribution(confidences)

        return AggregationReport(
            request_id=request_id,
            url=url,
            overall_verdict=overall_verdict,
            overall_confidence=overall_confidence,
            findings=aggregated_findings,
            pipeline_statuses=pipeline_statuses,
            summary=summary,
            confidence_distribution=confidence_dist,
        )

    @staticmethod
    def _normalize_verdict(verdict: str) -> OverallVerdict:
        """Normalize verdict to standard format."""
        verdict_lower = verdict.lower()
        if "supported" in verdict_lower:
            return OverallVerdict.SUPPORTED
        elif "disputed" in verdict_lower:
            return OverallVerdict.DISPUTED
        else:
            return OverallVerdict.UNVERIFIABLE

    @staticmethod
    def _calculate_overall_verdict(verdicts: list[str], confidences: list[int]) -> OverallVerdict:
        """Calculate overall verdict from pipeline results."""
        if not verdicts:
            return OverallVerdict.UNVERIFIABLE

        # Normalize verdicts
        normalized = [FindingAggregator._normalize_verdict(v) for v in verdicts]

        # Count verdict types
        supported = normalized.count(OverallVerdict.SUPPORTED)
        disputed = normalized.count(OverallVerdict.DISPUTED)
        unverifiable = normalized.count(OverallVerdict.UNVERIFIABLE)

        # Determine overall verdict based on consensus
        total = len(normalized)
        if supported / total >= 0.6:
            return OverallVerdict.SUPPORTED
        elif disputed / total >= 0.6:
            return OverallVerdict.DISPUTED
        elif unverifiable / total >= 0.7:
            return OverallVerdict.UNVERIFIABLE
        else:
            return OverallVerdict.MIXED

    @staticmethod
    def _calculate_overall_confidence(confidences: list[int]) -> int:
        """Calculate overall confidence from pipeline confidences."""
        if not confidences:
            return 0

        # Weight by pipeline weights and average
        # For MVP, use simple average
        avg_confidence = sum(confidences) / len(confidences)
        return int(min(100, max(0, avg_confidence)))

    @staticmethod
    def _generate_summary(verdict: OverallVerdict, finding_count: int) -> str:
        """Generate human-readable summary."""
        verdict_text = {
            OverallVerdict.SUPPORTED: "appears to be supported by evidence",
            OverallVerdict.DISPUTED: "appears to be disputed or contradicted",
            OverallVerdict.UNVERIFIABLE: "cannot be verified with available evidence",
            OverallVerdict.MIXED: "has mixed verification results across multiple pipelines",
        }

        return f"Content {verdict_text[verdict]} based on {finding_count} pipeline finding(s)."

    @staticmethod
    def _calculate_confidence_distribution(confidences: list[int]) -> dict[str, int]:
        """Calculate distribution of confidence scores."""
        if not confidences:
            return {}

        distribution = {
            "min": min(confidences),
            "max": max(confidences),
            "avg": int(sum(confidences) / len(confidences)),
            "total_pipelines": len(confidences),
        }

        # High confidence (80-100)
        high = sum(1 for c in confidences if c >= 80)
        # Medium confidence (50-79)
        medium = sum(1 for c in confidences if 50 <= c < 80)
        # Low confidence (0-49)
        low = sum(1 for c in confidences if c < 50)

        distribution["high_confidence"] = high
        distribution["medium_confidence"] = medium
        distribution["low_confidence"] = low

        return distribution


# Global singleton instance
_aggregator: Optional[FindingAggregator] = None


def get_finding_aggregator() -> FindingAggregator:
    """Get or create the global finding aggregator instance."""
    global _aggregator
    if _aggregator is None:
        _aggregator = FindingAggregator()
    return _aggregator


async def aggregate_findings_task(
    request_id: str,
    url: str,
    pipeline_results: dict[str, dict],
    timeout: int = 30,
) -> dict:
    """
    Async task wrapper for finding aggregation.

    Args:
        request_id: Request identifier
        url: URL being verified
        pipeline_results: Dictionary of pipeline results
        timeout: Aggregation timeout in seconds

    Returns:
        Dictionary representation of AggregationReport
    """
    # Convert dict results to PipelineResult objects
    converted_results = {}
    for pipeline_name, result_dict in pipeline_results.items():
        if isinstance(result_dict, dict):
            converted_results[pipeline_name] = PipelineResult(
                pipeline_name=pipeline_name,
                verdict=result_dict.get("verdict", "Unverifiable"),
                confidence=result_dict.get("confidence", 0),
                score=result_dict.get("score"),
                indicators_count=result_dict.get("indicators_count", 0),
                summary=result_dict.get("summary", ""),
                error=result_dict.get("error"),
            )
        else:
            converted_results[pipeline_name] = result_dict

    aggregator = get_finding_aggregator()
    report = await aggregator.aggregate_findings(
        request_id, url, converted_results, timeout=timeout
    )
    return report.to_dict()
