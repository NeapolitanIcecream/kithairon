"""Quality gate helpers for scored candidates."""

from __future__ import annotations

from typing import Literal

from kithairon.config import QualityConfig

type QualityStatus = Literal["good", "acceptable", "needs_repair", "needs_solver"]


def quality_status(
    score: float,
    quality: QualityConfig | None = None,
) -> QualityStatus:
    thresholds = quality or QualityConfig()
    if score >= thresholds.strict_good_score:
        return "good"
    if score >= thresholds.strict_min_acceptable_score:
        return "acceptable"
    if score >= thresholds.auto_solver_threshold:
        return "needs_repair"
    return "needs_solver"


def passes_quality_gate(score: float, quality: QualityConfig | None = None) -> bool:
    thresholds = quality or QualityConfig()
    return score >= thresholds.strict_min_acceptable_score
