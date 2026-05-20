"""Candidate scoring, ranking, and quality gates."""

from kithairon.scoring.breakdown import (
    PenaltyBreakdown,
    ScoreBreakdown,
    build_score_breakdown,
)
from kithairon.scoring.diversity import rank_candidates
from kithairon.scoring.musicality import (
    MusicalityBreakdown,
    MusicalityMetric,
    compute_musicality,
)
from kithairon.scoring.quality import QualityStatus, passes_quality_gate, quality_status
from kithairon.scoring.scorer import score_candidate, score_violations
from kithairon.scoring.weights import STYLE_PROFILES, StyleProfile, get_style_profile

__all__ = [
    "STYLE_PROFILES",
    "MusicalityBreakdown",
    "MusicalityMetric",
    "PenaltyBreakdown",
    "QualityStatus",
    "ScoreBreakdown",
    "StyleProfile",
    "build_score_breakdown",
    "compute_musicality",
    "get_style_profile",
    "passes_quality_gate",
    "quality_status",
    "rank_candidates",
    "score_candidate",
    "score_violations",
]
