"""Audio/video pipeline MVP heuristics for feature extraction and deepfake signals."""

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
                snippet=_evidence_snippet(item),
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
            details={
                "suspicious_count": len(suspicious),
                "total_media": total,
                "feature_extraction": _feature_summary(audio, video),
            },
        )
        return PipelineResult(verdict=Verdict.DISPUTED, confidence=55, findings=[finding])

    failed_downloads = [item for item in (audio + video) if item.download_error]
    if failed_downloads:
        finding = Finding(
            summary="Some audio/video assets could not be downloaded, so deepfake analysis is inconclusive.",
            verdict=Verdict.UNVERIFIABLE,
            confidence=35,
            evidence=evidence,
            details={
                "failed_downloads": len(failed_downloads),
                "total_media": total,
                "feature_extraction": _feature_summary(audio, video),
            },
        )
        return PipelineResult(verdict=Verdict.UNVERIFIABLE, confidence=35, findings=[finding])

    finding = Finding(
        summary="Media assets detected, but no strong deepfake markers were observed in URL-level heuristics.",
        verdict=Verdict.UNVERIFIABLE,
        confidence=40,
        evidence=evidence,
        details={"total_media": total, "feature_extraction": _feature_summary(audio, video)},
    )
    return PipelineResult(verdict=Verdict.UNVERIFIABLE, confidence=40, findings=[finding])


def _evidence_snippet(item: MediaItem) -> str:
    if item.local_path:
        return f"Media candidate extracted and stored ({item.media_type}, {item.size_bytes or 0} bytes)."
    if item.download_error:
        return f"Media candidate extracted but not downloaded: {item.download_error}"
    return f"Media candidate extracted ({item.media_type})"


def _feature_summary(audio: List[MediaItem], video: List[MediaItem]) -> dict:
    downloaded_audio = [item for item in audio if item.local_path]
    downloaded_video = [item for item in video if item.local_path]
    return {
        "audio_items": len(audio),
        "video_items": len(video),
        "downloaded_audio": len(downloaded_audio),
        "downloaded_video": len(downloaded_video),
        "available_features": ["container_metadata", "file_size"] if downloaded_audio or downloaded_video else [],
    }
