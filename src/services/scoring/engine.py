"""Credibility score and summary generation services."""

from __future__ import annotations

from typing import Dict, List, Tuple

from src.api.models.schemas import Findings, PipelineResult, Verdict


DEFAULT_WEIGHTS: Dict[str, float] = {
    "text": 0.4,
    "image": 0.2,
    "audio_video": 0.2,
    "spam": 0.2,
}

VERDICT_FACTORS: Dict[Verdict, float] = {
    Verdict.SUPPORTED: 1.0,
    Verdict.UNVERIFIABLE: 0.6,
    Verdict.DISPUTED: 0.2,
}


def _normalize_verdict(verdict: Verdict | str) -> Verdict:
    """Normalize enum/string verdict values into Verdict enum."""
    if isinstance(verdict, Verdict):
        return verdict
    normalized = str(verdict).strip().lower()
    if normalized == "supported":
        return Verdict.SUPPORTED
    if normalized == "disputed":
        return Verdict.DISPUTED
    return Verdict.UNVERIFIABLE


def _pipeline_score(result: PipelineResult) -> float:
    """Project a pipeline result into a normalized score."""
    factor = VERDICT_FACTORS.get(_normalize_verdict(result.verdict), 0.6)
    return max(0.0, min(100.0, result.confidence * factor))


def compute_overall_credibility_score(findings: Findings) -> int:
    """Compute weighted credibility score from available pipelines."""
    weighted_scores: List[Tuple[float, float]] = []

    for key in ("text", "image", "audio_video", "spam"):
        result = getattr(findings, key)
        if result is None:
            continue
        weight = DEFAULT_WEIGHTS.get(key, 0.0)
        weighted_scores.append((_pipeline_score(result), weight))

    if not weighted_scores:
        return 0

    total_weight = sum(weight for _, weight in weighted_scores)
    if total_weight <= 0:
        return int(sum(score for score, _ in weighted_scores) / len(weighted_scores))

    aggregate = sum(score * weight for score, weight in weighted_scores) / total_weight
    return int(round(max(0.0, min(100.0, aggregate))))


def generate_human_summary(findings: Findings, overall_score: int) -> str:
    """Generate concise human-readable findings summary."""
    active = []
    disputed = []
    supported = []
    unverifiable = []

    for key in ("text", "image", "audio_video", "spam"):
        result = getattr(findings, key)
        if result is None:
            continue
        verdict = _normalize_verdict(result.verdict)
        active.append(f"{key}:{verdict.value}({result.confidence})")
        if verdict == Verdict.DISPUTED:
            disputed.append(key)
        elif verdict == Verdict.SUPPORTED:
            supported.append(key)
        else:
            unverifiable.append(key)

    if not active:
        return "No analyzable evidence was available for this URL."

    if disputed:
        lead = f"Potential misinformation signals detected in {', '.join(disputed)} analysis."
    elif supported:
        lead = f"Content appears broadly credible based on {', '.join(supported)} analysis."
    else:
        lead = "Most signals are inconclusive, so evidence remains limited."

    return (
        f"{lead} Overall credibility score: {overall_score}/100. "
        f"Pipeline verdicts: {', '.join(active)}."
    )
