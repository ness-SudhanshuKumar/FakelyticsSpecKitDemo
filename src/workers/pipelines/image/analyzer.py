"""Image pipeline MVP heuristics for manipulation, source context, and forensics."""

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
            snippet=_evidence_snippet(image),
            title=image.title or "Extracted image",
        )
        for image in images[:5]
    ]

    suspicious = [
        image
        for image in images
        if any(marker in image.url.lower() for marker in ("ai", "generated", "deepfake", "synthetic"))
    ]
    failed_downloads = [image for image in images if image.download_error]
    if suspicious:
        finding = Finding(
            summary="Some images contain synthetic-content indicators in their source URLs.",
            verdict=Verdict.DISPUTED,
            confidence=60,
            evidence=evidence,
            details={
                "suspicious_count": len(suspicious),
                "total_images": len(images),
                "reverse_search_status": "not_configured",
                "forensics": _forensics_summary(images),
            },
        )
        return PipelineResult(verdict=Verdict.DISPUTED, confidence=55, findings=[finding])

    if failed_downloads:
        finding = Finding(
            summary="One or more extracted images could not be downloaded or validated for forensic checks.",
            verdict=Verdict.UNVERIFIABLE,
            confidence=35,
            evidence=evidence,
            details={
                "failed_downloads": len(failed_downloads),
                "total_images": len(images),
                "reverse_search_status": "not_configured",
                "forensics": _forensics_summary(images),
            },
        )
        return PipelineResult(verdict=Verdict.UNVERIFIABLE, confidence=35, findings=[finding])

    finding = Finding(
        summary="Images were detected, with no clear manipulation indicators from available metadata-level checks.",
        verdict=Verdict.UNVERIFIABLE,
        confidence=45,
        evidence=evidence,
        details={
            "total_images": len(images),
            "reverse_search_status": "not_configured",
            "forensics": _forensics_summary(images),
        },
    )
    return PipelineResult(verdict=Verdict.UNVERIFIABLE, confidence=45, findings=[finding])


def _evidence_snippet(image: MediaItem) -> str:
    if image.local_path:
        return f"Image downloaded for analysis ({image.size_bytes or 0} bytes)."
    if image.download_error:
        return f"Image discovered but not downloaded: {image.download_error}"
    return f"Image candidate discovered: {image.url}"


def _forensics_summary(images: List[MediaItem]) -> dict:
    downloaded = [image for image in images if image.local_path]
    return {
        "downloaded_count": len(downloaded),
        "metadata_available": bool(downloaded),
        "checked_signals": ["file_type", "content_type", "download_integrity"],
    }
