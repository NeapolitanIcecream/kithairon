"""Penalty breakdown models for score reporting."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from kithairon.ir import RuleViolation, ViolationSeverity
from kithairon.scoring.weights import StyleProfile


@dataclass(frozen=True)
class PenaltyBreakdown:
    rule_id: str
    severity: ViolationSeverity
    base_penalty: float
    rule_weight: float
    severity_weight: float
    weighted_penalty: float
    message: str
    bar: int | None
    beat: Fraction | None

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "base_penalty": self.base_penalty,
            "rule_weight": self.rule_weight,
            "severity_weight": self.severity_weight,
            "weighted_penalty": self.weighted_penalty,
            "message": self.message,
            "bar": self.bar,
            "beat": str(self.beat) if self.beat is not None else None,
        }


@dataclass(frozen=True)
class ScoreBreakdown:
    base_score: float
    total_penalty: float
    final_score: float
    penalties: tuple[PenaltyBreakdown, ...]

    @property
    def top_penalties(self) -> tuple[PenaltyBreakdown, ...]:
        return tuple(
            sorted(
                self.penalties,
                key=lambda penalty: penalty.weighted_penalty,
                reverse=True,
            )[:5]
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "base_score": self.base_score,
            "total_penalty": self.total_penalty,
            "final_score": self.final_score,
            "penalties": [penalty.to_dict() for penalty in self.penalties],
            "top_penalties": [penalty.to_dict() for penalty in self.top_penalties],
        }


def build_score_breakdown(
    violations: tuple[RuleViolation, ...],
    profile: StyleProfile,
    *,
    base_score: float = 100.0,
) -> ScoreBreakdown:
    penalties = tuple(_penalty_breakdown(violation, profile) for violation in violations)
    total_penalty = sum(penalty.weighted_penalty for penalty in penalties)
    final_score = max(0.0, min(100.0, base_score - total_penalty))
    return ScoreBreakdown(
        base_score=base_score,
        total_penalty=total_penalty,
        final_score=round(final_score, 2),
        penalties=penalties,
    )


def _penalty_breakdown(
    violation: RuleViolation,
    profile: StyleProfile,
) -> PenaltyBreakdown:
    rule_weight = profile.weight_for_rule(violation.rule_id)
    severity_weight = profile.weight_for_severity(violation.severity)
    weighted_penalty = violation.penalty * rule_weight * severity_weight
    return PenaltyBreakdown(
        rule_id=violation.rule_id,
        severity=violation.severity,
        base_penalty=violation.penalty,
        rule_weight=rule_weight,
        severity_weight=severity_weight,
        weighted_penalty=round(weighted_penalty, 2),
        message=violation.message,
        bar=violation.bar,
        beat=violation.beat,
    )
