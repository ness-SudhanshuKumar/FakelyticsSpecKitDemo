"""Image pipeline MVP heuristics (T-401/T-402/T-403 starter)."""

from __future__ import annotations

from typing import List

from src.api.models.schemas import Evidence, Finding, PipelineResult, Verdict
from src.core.extraction.service import MediaItem


def analyze_images(images: List[MediaItem]) -> PipelineResult | None:
    """Analyze extracted images for basic credibility indicators."""
    if not images:
        return None

    evidence = [
        Evidence(
            url=image.url,
            snippet=f"Image candidate discovered: {image.url}",
            title=image.title or "Extracted image",
        )
        for image in images[:5]
    ]

    suspicious = [image for image in images if "ai" in image.url.lower() or "generated" in image.url.lower()]
    if suspicious:
        finding = Finding(
            summary="Some images contain AI/synthetic-like URL indicators.",
            verdict=Verdict.DISPUTED,
            confidence=60,
            evidence=evidence,
            details={"suspicious_count": len(suspicious), "total_images": len(images)},
        )
        return PipelineResult(verdict=Verdict.DISPUTED, confidence=55, findings=[finding])

    finding = Finding(
        summary="Images were detected, but no clear manipulation indicators were found in metadata-level heuristics.",
        verdict=Verdict.UNVERIFIABLE,
        confidence=45,
        evidence=evidence,
        details={"total_images": len(images)},
    )
    return PipelineResult(verdict=Verdict.UNVERIFIABLE, confidence=45, findings=[finding])

