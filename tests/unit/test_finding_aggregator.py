"""Unit tests for finding aggregation module (T-701)."""

import pytest

from src.workers.pipelines.aggregation.finding_aggregator import (
    OverallVerdict,
    PipelineResult,
    AggregatedFinding,
    AggregationReport,
    FindingAggregator,
    get_finding_aggregator,
    aggregate_findings_task,
)


class TestPipelineResult:
    """Tests for PipelineResult dataclass."""

    def test_pipeline_result_success(self):
        """Test creating successful pipeline result."""
        result = PipelineResult(
            pipeline_name="text",
            verdict="Disputed",
            confidence=75,
            indicators_count=5,
            summary="Text analysis found disputed content"
        )
        assert result.pipeline_name == "text"
        assert result.confidence == 75
        assert result.error is None

    def test_pipeline_result_error(self):
        """Test creating pipeline result with error."""
        result = PipelineResult(
            pipeline_name="image",
            verdict="Unverifiable",
            confidence=0,
            error="Image analysis failed"
        )
        assert result.error == "Image analysis failed"

    def test_pipeline_result_to_dict(self):
        """Test converting result to dict."""
        result = PipelineResult(
            pipeline_name="text",
            verdict="Supported",
            confidence=85,
            score=90
        )
        d = result.to_dict()
        assert d["pipeline_name"] == "text"
        assert d["confidence"] == 85


class TestAggregatedFinding:
    """Tests for AggregatedFinding dataclass."""

    def test_aggregated_finding_creation(self):
        """Test creating aggregated finding."""
        finding = AggregatedFinding(
            finding_id="req1_text",
            finding_type="text",
            verdict=OverallVerdict.DISPUTED,
            confidence=70,
            summary="Text contains disputed claims",
            source_pipelines=["text"]
        )
        assert finding.finding_type == "text"
        assert finding.verdict == OverallVerdict.DISPUTED

    def test_aggregated_finding_to_dict(self):
        """Test converting finding to dict."""
        finding = AggregatedFinding(
            finding_id="req1_spam",
            finding_type="spam",
            verdict=OverallVerdict.SUPPORTED,
            confidence=80,
            summary="Content flagged as spam",
            source_pipelines=["spam"]
        )
        d = finding.to_dict()
        assert d["verdict"] == "supported"
        assert d["finding_type"] == "spam"


class TestAggregationReport:
    """Tests for AggregationReport dataclass."""

    def test_aggregation_report_creation(self):
        """Test creating aggregation report."""
        report = AggregationReport(
            request_id="req123",
            url="https://example.com",
            overall_verdict=OverallVerdict.DISPUTED,
            overall_confidence=75,
            findings=[],
            pipeline_statuses={"text": "completed"},
            summary="Content is disputed"
        )
        assert report.request_id == "req123"
        assert report.overall_verdict == OverallVerdict.DISPUTED

    def test_aggregation_report_to_dict(self):
        """Test converting report to dict."""
        report = AggregationReport(
            request_id="req456",
            url="https://test.com",
            overall_verdict=OverallVerdict.UNVERIFIABLE,
            overall_confidence=45,
            findings=[],
            pipeline_statuses={"text": "completed", "spam": "error"},
            summary="Cannot verify content"
        )
        d = report.to_dict()
        assert d["overall_verdict"] == "unverifiable"
        assert d["overall_confidence"] == 45


class TestFindingAggregator:
    """Tests for FindingAggregator class."""

    @pytest.mark.asyncio
    async def test_aggregate_empty_request_id_raises_error(self):
        """Test that empty request_id raises ValueError."""
        aggregator = FindingAggregator()
        with pytest.raises(ValueError, match="Invalid request_id"):
            await aggregator.aggregate_findings("", "https://example.com", {})

    @pytest.mark.asyncio
    async def test_aggregate_none_url_raises_error(self):
        """Test that None url raises ValueError."""
        aggregator = FindingAggregator()
        with pytest.raises(ValueError, match="Invalid url"):
            await aggregator.aggregate_findings("req1", None, {})

    @pytest.mark.asyncio
    async def test_aggregate_empty_pipeline_results_raises_error(self):
        """Test that empty pipeline_results raises ValueError."""
        aggregator = FindingAggregator()
        with pytest.raises(ValueError, match="Invalid pipeline_results"):
            await aggregator.aggregate_findings("req1", "https://example.com", {})

    @pytest.mark.asyncio
    async def test_aggregate_single_pipeline(self):
        """Test aggregating result from single pipeline."""
        aggregator = FindingAggregator()
        results = {
            "text": PipelineResult(
                pipeline_name="text",
                verdict="Supported",
                confidence=85,
                summary="Text appears supported"
            )
        }
        report = await aggregator.aggregate_findings(
            "req1", "https://example.com", results
        )
        assert report.overall_verdict == OverallVerdict.SUPPORTED
        assert report.overall_confidence == 85
        assert len(report.findings) == 1

    @pytest.mark.asyncio
    async def test_aggregate_multiple_pipelines_consensus(self):
        """Test aggregating results with pipeline consensus."""
        aggregator = FindingAggregator()
        results = {
            "text": PipelineResult(
                pipeline_name="text",
                verdict="Disputed",
                confidence=70,
                summary="Text analysis"
            ),
            "spam": PipelineResult(
                pipeline_name="spam",
                verdict="Disputed",
                confidence=75,
                summary="Spam analysis"
            ),
        }
        report = await aggregator.aggregate_findings(
            "req1", "https://example.com", results
        )
        assert report.overall_verdict == OverallVerdict.DISPUTED
        assert report.overall_confidence > 0
        assert len(report.findings) == 2

    @pytest.mark.asyncio
    async def test_aggregate_mixed_verdicts(self):
        """Test aggregating mixed verdicts from pipelines."""
        aggregator = FindingAggregator()
        results = {
            "text": PipelineResult(
                pipeline_name="text",
                verdict="Supported",
                confidence=80,
            ),
            "spam": PipelineResult(
                pipeline_name="spam",
                verdict="Unverifiable",
                confidence=40,
            ),
        }
        report = await aggregator.aggregate_findings(
            "req1", "https://example.com", results
        )
        # Mixed verdicts should result in mixed or unverifiable
        assert report.overall_verdict in [
            OverallVerdict.MIXED,
            OverallVerdict.UNVERIFIABLE
        ]

    @pytest.mark.asyncio
    async def test_aggregate_pipeline_error_handling(self):
        """Test handling pipeline errors gracefully."""
        aggregator = FindingAggregator()
        results = {
            "text": PipelineResult(
                pipeline_name="text",
                verdict="Supported",
                confidence=85,
                summary="Text analysis"
            ),
            "image": PipelineResult(
                pipeline_name="image",
                verdict="Unverifiable",
                confidence=0,
                error="Image processing failed"
            ),
        }
        report = await aggregator.aggregate_findings(
            "req1", "https://example.com", results
        )
        # Should still generate report with error pipeline marked
        assert report.pipeline_statuses["image"] == "error"
        assert len(report.findings) >= 1

    @pytest.mark.asyncio
    async def test_aggregate_returns_valid_structure(self):
        """Test that report has valid structure."""
        aggregator = FindingAggregator()
        results = {
            "text": PipelineResult(
                pipeline_name="text",
                verdict="Disputed",
                confidence=70,
            )
        }
        report = await aggregator.aggregate_findings(
            "req1", "https://example.com", results
        )
        assert hasattr(report, "request_id")
        assert hasattr(report, "url")
        assert hasattr(report, "overall_verdict")
        assert hasattr(report, "overall_confidence")
        assert hasattr(report, "findings")
        assert hasattr(report, "pipeline_statuses")
        assert hasattr(report, "summary")

    def test_normalize_verdict_supported(self):
        """Test normalizing 'Supported' verdict."""
        verdict = FindingAggregator._normalize_verdict("Supported")
        assert verdict == OverallVerdict.SUPPORTED

    def test_normalize_verdict_disputed(self):
        """Test normalizing 'Disputed' verdict."""
        verdict = FindingAggregator._normalize_verdict("Disputed")
        assert verdict == OverallVerdict.DISPUTED

    def test_normalize_verdict_unverifiable(self):
        """Test normalizing unverifiable verdict."""
        verdict = FindingAggregator._normalize_verdict("Unverifiable")
        assert verdict == OverallVerdict.UNVERIFIABLE

    def test_normalize_verdict_case_insensitive(self):
        """Test verdict normalization is case-insensitive."""
        assert FindingAggregator._normalize_verdict("SUPPORTED") == OverallVerdict.SUPPORTED
        assert FindingAggregator._normalize_verdict("disputed") == OverallVerdict.DISPUTED

    def test_calculate_overall_verdict_all_supported(self):
        """Test calculating overall verdict with all supported."""
        verdicts = ["Supported", "Supported", "Supported"]
        confidences = [85, 80, 90]
        verdict = FindingAggregator._calculate_overall_verdict(verdicts, confidences)
        assert verdict == OverallVerdict.SUPPORTED

    def test_calculate_overall_verdict_all_disputed(self):
        """Test calculating overall verdict with all disputed."""
        verdicts = ["Disputed", "Disputed", "Disputed"]
        confidences = [75, 70, 80]
        verdict = FindingAggregator._calculate_overall_verdict(verdicts, confidences)
        assert verdict == OverallVerdict.DISPUTED

    def test_calculate_overall_verdict_mostly_unverifiable(self):
        """Test calculating verdict with mostly unverifiable."""
        verdicts = ["Unverifiable", "Unverifiable", "Unverifiable"]
        confidences = [30, 25, 35]
        verdict = FindingAggregator._calculate_overall_verdict(verdicts, confidences)
        assert verdict == OverallVerdict.UNVERIFIABLE

    def test_calculate_overall_confidence_empty(self):
        """Test calculating confidence with empty list."""
        confidence = FindingAggregator._calculate_overall_confidence([])
        assert confidence == 0

    def test_calculate_overall_confidence_single(self):
        """Test calculating confidence with single value."""
        confidence = FindingAggregator._calculate_overall_confidence([75])
        assert confidence == 75

    def test_calculate_overall_confidence_multiple(self):
        """Test calculating confidence with multiple values."""
        confidence = FindingAggregator._calculate_overall_confidence([80, 70, 90])
        assert 70 <= confidence <= 90

    def test_calculate_confidence_distribution(self):
        """Test calculating confidence distribution."""
        confidences = [85, 75, 50, 40, 25]
        dist = FindingAggregator._calculate_confidence_distribution(confidences)
        assert dist["min"] == 25
        assert dist["max"] == 85
        assert dist["total_pipelines"] == 5
        assert dist["high_confidence"] == 1  # Only 85 (>=80)
        assert dist["medium_confidence"] == 2  # 75, 50 (50-79)
        assert dist["low_confidence"] == 2  # 40, 25 (< 50)


class TestGlobalInstances:
    """Tests for global singleton instances."""

    @pytest.mark.asyncio
    async def test_get_finding_aggregator_singleton(self):
        """Test that get_finding_aggregator returns same instance."""
        agg1 = get_finding_aggregator()
        agg2 = get_finding_aggregator()
        assert agg1 is agg2

    @pytest.mark.asyncio
    async def test_aggregate_findings_task(self):
        """Test async task wrapper."""
        results = {
            "text": {
                "verdict": "Disputed",
                "confidence": 70,
                "summary": "Text analysis"
            }
        }
        report_dict = await aggregate_findings_task(
            "req1", "https://example.com", results
        )
        assert isinstance(report_dict, dict)
        assert "overall_verdict" in report_dict
        assert "overall_confidence" in report_dict


class TestRealWorldScenarios:
    """Tests for real-world aggregation scenarios."""

    @pytest.mark.asyncio
    async def test_aggregate_all_pipelines_success(self):
        """Test aggregating results from all pipelines successfully."""
        aggregator = FindingAggregator()
        results = {
            "text": PipelineResult(
                pipeline_name="text",
                verdict="Disputed",
                confidence=75,
                indicators_count=5,
                summary="Text contains disputed claims"
            ),
            "spam": PipelineResult(
                pipeline_name="spam",
                verdict="Suspicious",
                confidence=65,
                indicators_count=3,
                summary="Content shows spam patterns"
            ),
            "source": PipelineResult(
                pipeline_name="source",
                verdict="Low Credibility",
                confidence=45,
                indicators_count=2,
                summary="Source has low credibility"
            ),
        }
        report = await aggregator.aggregate_findings(
            "req1", "https://example.com", results
        )
        assert len(report.findings) == 3
        assert report.overall_confidence > 0

    @pytest.mark.asyncio
    async def test_aggregate_with_high_confidence_consensus(self):
        """Test aggregation with high-confidence consensus."""
        aggregator = FindingAggregator()
        results = {
            "text": PipelineResult(
                pipeline_name="text",
                verdict="Supported",
                confidence=95,
            ),
            "source": PipelineResult(
                pipeline_name="source",
                verdict="Supported",  # Changed from "Highly Credible" to "Supported"
                confidence=90,
            ),
        }
        report = await aggregator.aggregate_findings(
            "req1", "https://wikipedia.org", results
        )
        assert report.overall_verdict == OverallVerdict.SUPPORTED
        assert report.overall_confidence >= 85

    @pytest.mark.asyncio
    async def test_aggregate_low_confidence_content(self):
        """Test aggregating low-confidence content."""
        aggregator = FindingAggregator()
        results = {
            "text": PipelineResult(
                pipeline_name="text",
                verdict="Unverifiable",
                confidence=35,
            ),
            "spam": PipelineResult(
                pipeline_name="spam",
                verdict="Suspicious",
                confidence=40,
            ),
        }
        report = await aggregator.aggregate_findings(
            "req1", "https://unknown.com", results
        )
        assert report.overall_confidence < 50
