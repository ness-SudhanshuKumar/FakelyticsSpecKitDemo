"""Tests for API text-pipeline orchestration."""

import pytest

from src.api.models.schemas import Findings, PipelineResult, Verdict
from src.core.extraction.service import ContentExtract
from src.services.orchestration.verification import _build_text_result
from src.services.scoring import generate_human_summary


@pytest.mark.asyncio
async def test_text_result_includes_nlp_when_factcheck_has_no_external_evidence():
    content = ContentExtract(
        url="https://example.com/news",
        text_content=(
            "Reports indicate that the newly elected government will face a floor test on May 13. "
            "The ceremony was attended by senior officials and party leaders."
        ),
    )

    result = await _build_text_result(content)

    assert result.confidence > 0
    assert any(finding.details.get("pipeline") == "text_nlp" for finding in result.findings)
    assert any(
        finding.details.get("pipeline") == "text_factcheck"
        for finding in result.findings
        if finding.details
    )


def test_low_score_summary_does_not_claim_broad_credibility_from_spam_only():
    findings = Findings(
        text=PipelineResult(verdict=Verdict.UNVERIFIABLE, confidence=0, findings=[]),
        image=PipelineResult(verdict=Verdict.UNVERIFIABLE, confidence=35, findings=[]),
        spam=PipelineResult(verdict=Verdict.SUPPORTED, confidence=80, findings=[]),
    )

    summary = generate_human_summary(findings, overall_score=25)

    assert "weak or inconclusive" in summary
    assert "broadly credible" not in summary
