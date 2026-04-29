"""Spam and source-credibility heuristics (T-601/T-602 MVP)."""

from __future__ import annotations

from typing import List
from urllib.parse import urlparse

from src.api.models.schemas import Evidence, Finding, PipelineResult, Verdict


SUSPICIOUS_TERMS = {
    "free money",
    "guaranteed",
    "urgent action",
    "click here",
    "limited time",
    "bitcoin giveaway",
    "act now",
}

LOW_CRED_TLDS = {".xyz", ".top", ".click", ".work"}


def analyze_spam_and_source(url: str, text: str) -> PipelineResult:
    """Run lightweight spam/source credibility analysis for MVP."""
    findings: List[Finding] = []
    lowered = text.lower()
    matches = [term for term in SUSPICIOUS_TERMS if term in lowered]

    hostname = (urlparse(url).hostname or "").lower()
    tld_suspicious = any(hostname.endswith(tld) for tld in LOW_CRED_TLDS)

    confidence = 80
    verdict = Verdict.SUPPORTED

    if matches:
        findings.append(
            Finding(
                summary=f"Spam-like language detected: {', '.join(matches[:3])}",
                verdict=Verdict.DISPUTED,
                confidence=85,
                evidence=[
                    Evidence(
                        url=url,
                        snippet=f"Detected suspicious terms: {', '.join(matches[:3])}",
                        title="Spam Pattern Match",
                    )
                ],
                details={"matched_terms": matches[:10]},
            )
        )
        verdict = Verdict.DISPUTED
        confidence = 35

    if tld_suspicious:
        findings.append(
            Finding(
                summary=f"Domain uses high-risk TLD: {hostname}",
                verdict=Verdict.DISPUTED,
                confidence=70,
                evidence=[
                    Evidence(
                        url=url,
                        snippet=f"Domain {hostname} matched a high-risk TLD category.",
                        title="Domain Reputation Heuristic",
                    )
                ],
            )
        )
        verdict = Verdict.DISPUTED
        confidence = min(confidence, 40)

    if not findings:
        findings.append(
            Finding(
                summary="No major spam patterns detected in source and content.",
                verdict=Verdict.SUPPORTED,
                confidence=80,
                evidence=[
                    Evidence(
                        url=url,
                        snippet="Source text does not match known spam heuristic patterns.",
                        title="Spam Heuristic Baseline",
                    )
                ],
            )
        )

    return PipelineResult(verdict=verdict, confidence=confidence, findings=findings)

