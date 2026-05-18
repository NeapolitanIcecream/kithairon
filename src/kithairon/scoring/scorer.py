"""Candidate scoring orchestration."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from kithairon.analysis import AnalysisContext, analyze_candidate
from kithairon.config import QualityConfig
from kithairon.ir import CanonCandidate, RuleViolation
from kithairon.rules import Rule, evaluate_rules
from kithairon.scoring.breakdown import ScoreBreakdown, build_score_breakdown
from kithairon.scoring.quality import quality_status
from kithairon.scoring.weights import get_style_profile


def score_candidate(
    candidate: CanonCandidate,
    *,
    context: AnalysisContext | None = None,
    rules: Sequence[Rule] | None = None,
    profile_name: str = "pop-lite",
    quality: QualityConfig | None = None,
) -> CanonCandidate:
    analysis_context = context or analyze_candidate(candidate)
    violations = evaluate_rules(candidate, analysis_context, rules)
    breakdown = score_violations(violations, profile_name=profile_name)
    metadata = {
        **candidate.metadata,
        "score_profile": profile_name,
        "score_breakdown": breakdown.to_dict(),
        "quality_status": quality_status(breakdown.final_score, quality),
    }
    return replace(
        candidate,
        score=breakdown.final_score,
        violations=violations,
        metadata=metadata,
    )


def score_violations(
    violations: tuple[RuleViolation, ...],
    *,
    profile_name: str = "pop-lite",
) -> ScoreBreakdown:
    profile = get_style_profile(profile_name)
    return build_score_breakdown(violations, profile)
