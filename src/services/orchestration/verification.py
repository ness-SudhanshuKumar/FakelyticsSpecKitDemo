"""Verification orchestration service (pipeline aggregation + report assembly)."""

from __future__ import annotations

from datetime import datetime
from statistics import mean
from typing import List
from uuid import UUID

from src.api.models.schemas import (
    CredibilityReport,
    Evidence,
    Finding,
    Findings,
    PipelineResult,
    Verdict,
)
from src.core.config.settings import settings
from src.core.extraction.service import ContentExtract
from src.services.evidence import validate_evidence_sources
from src.services.scoring import compute_overall_credibility_score, generate_human_summary
from src.workers.pipelines.audio_video import analyze_audio_video
from src.workers.pipelines.image import analyze_images
from src.workers.pipelines.spam import analyze_spam_and_source
from src.workers.pipelines.text.factchecker import ClaimFinding, get_fact_checker
from src.workers.pipelines.text.nlp_analyzer import NLPFinding, get_nlp_analyzer
from src.workers.pipelines.text.preprocessor import get_preprocessor


def _verdict_from_text(value: str) -> Verdict:
    normalized = (value or "").strip().lower()
    if normalized == "supported":
        return Verdict.SUPPORTED
    if normalized == "disputed":
        return Verdict.DISPUTED
    return Verdict.UNVERIFIABLE


async def _convert_claim_finding(claim_finding: ClaimFinding) -> Finding:
    evidence_items = [
        Evidence(
            url=item.url,
            snippet=item.snippet,
            title=item.title or item.source,
        )
        for item in claim_finding.evidence
    ]
    evidence_items = await validate_evidence_sources(evidence_items)
    return Finding(
        summary=claim_finding.summary,
        verdict=_verdict_from_text(claim_finding.verdict.value),
        confidence=max(0, min(100, int(claim_finding.confidence))),
        evidence=evidence_items,
        details={"claim": claim_finding.claim, "pipeline": claim_finding.pipeline},
    )


def _convert_nlp_finding(nlp_finding: NLPFinding) -> Finding:
    """Convert NLP language-pattern analysis into the API finding model."""
    return Finding(
        summary=nlp_finding.summary,
        verdict=_verdict_from_text(nlp_finding.verdict.value),
        confidence=max(0, min(100, int(nlp_finding.confidence))),
        evidence=[],
        details={
            "pipeline": "text_nlp",
            "language_indicators": nlp_finding.language_indicators,
            "recommendation": nlp_finding.recommendation,
            "patterns": [pattern.to_dict() for pattern in nlp_finding.patterns],
        },
    )


def _is_unverified_factcheck(finding: Finding) -> bool:
    """Return True when a fact-check finding has no external evidence."""
    return (
        finding.details is not None
        and finding.details.get("pipeline") == "text_factcheck"
        and finding.verdict == Verdict.UNVERIFIABLE
        and not finding.evidence
    )


def _select_text_verdict(findings: List[Finding]) -> tuple[Verdict, int]:
    """Select a text verdict without letting no-evidence fact checks erase NLP analysis."""
    disputed = [item for item in findings if item.verdict == Verdict.DISPUTED]
    if disputed:
        return Verdict.DISPUTED, int(mean(item.confidence for item in disputed))

    supported = [item for item in findings if item.verdict == Verdict.SUPPORTED]
    if supported:
        evidence_backed = [item for item in supported if item.evidence]
        selected = evidence_backed or supported
        return Verdict.SUPPORTED, int(mean(item.confidence for item in selected))

    actionable = [item for item in findings if not _is_unverified_factcheck(item)]
    selected = actionable or findings
    return Verdict.UNVERIFIABLE, int(mean(item.confidence for item in selected))


async def _build_text_result(content: ContentExtract) -> PipelineResult:
    preprocessor = get_preprocessor()
    preprocessed = preprocessor.extract_and_preprocess(content)

    checker = get_fact_checker()
    claim_findings = await checker.check_preprocessed_text(
        preprocessed,
        timeout=settings.PIPELINE_TIMEOUT,
    )
    nlp_finding = await get_nlp_analyzer().analyze_preprocessed(
        preprocessed,
        timeout=settings.PIPELINE_TIMEOUT,
    )

    converted_findings: List[Finding] = []
    for item in claim_findings:
        converted_findings.append(await _convert_claim_finding(item))
    converted_findings.append(_convert_nlp_finding(nlp_finding))

    if not converted_findings:
        return PipelineResult(
            verdict=Verdict.UNVERIFIABLE,
            confidence=25,
            findings=[
                Finding(
                    summary="No explicit factual claims were confidently extracted for verification.",
                    verdict=Verdict.UNVERIFIABLE,
                    confidence=25,
                    evidence=[],
                    details={"claims_checked": 0},
                )
            ],
        )

    final_verdict, confidence = _select_text_verdict(converted_findings)
    return PipelineResult(verdict=final_verdict, confidence=confidence, findings=converted_findings)


async def build_credibility_report(
    request_id: UUID,
    url: str,
    content: ContentExtract,
) -> CredibilityReport:
    """Run available pipelines and build a final credibility report."""
    text_result = await _build_text_result(content)
    image_result = analyze_images(content.images)
    audio_video_result = analyze_audio_video(content.audio, content.video)
    spam_result = analyze_spam_and_source(url=url, text=content.text_content)

    findings = Findings(
        text=text_result,
        image=image_result,
        audio_video=audio_video_result,
        spam=spam_result,
    )

    overall_score = compute_overall_credibility_score(findings)
    summary = generate_human_summary(findings, overall_score)

    return CredibilityReport(
        request_id=request_id,
        url=url,
        overall_credibility_score=overall_score,
        summary=summary,
        findings=findings,
        timestamp=datetime.utcnow(),
    )
