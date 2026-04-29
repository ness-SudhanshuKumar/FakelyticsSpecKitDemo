"""Audio/video pipeline MVP heuristics (T-501/T-502/T-503 starter)."""

from __future__ import annotations

from typing import List

from src.api.models.schemas import Evidence, Finding, PipelineResult, Verdict
from src.core.extraction.service import MediaItem


def analyze_audio_video(audio: List[MediaItem], video: List[MediaItem]) -> PipelineResult | None:
    """Analyze extracted audio/video items for lightweight deepfake indicators."""
    total = len(audio) + len(video)
    if total == 0:
        return None

    evidence: List[Evidence] = []
    for item in (audio + video)[:5]:
        evidence.append(
            Evidence(
                url=item.url,
                snippet=f"Media candidate extracted ({item.media_type})",
                title=item.title or f"{item.media_type.title()} asset",
            )
        )

    suspicious = [
        item
        for item in (audio + video)
        if any(marker in item.url.lower() for marker in ("deepfake", "faceswap", "voiceclone", "synthetic"))
    ]

    if suspicious:
        finding = Finding(
            summary="Media URLs include markers associated with synthetic content workflows.",
            verdict=Verdict.DISPUTED,
            confidence=58,
            evidence=evidence,
            details={"suspicious_count": len(suspicious), "total_media": total},
        )
        return PipelineResult(verdict=Verdict.DISPUTED, confidence=55, findings=[finding])

    finding = Finding(
        summary="Media assets detected, but no strong deepfake markers were observed in URL-level heuristics.",
        verdict=Verdict.UNVERIFIABLE,
        confidence=40,
        evidence=evidence,
        details={"total_media": total},
    )
    return PipelineResult(verdict=Verdict.UNVERIFIABLE, confidence=40, findings=[finding])

