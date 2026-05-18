"""Vertical consonance and dissonance rules."""

from __future__ import annotations

from dataclasses import dataclass

from kithairon.analysis import AnalysisContext, Verticality
from kithairon.ir import CanonCandidate, RuleViolation

CONSONANT_SIMPLE_SEMITONES = frozenset({0, 3, 4, 7, 8, 9})


def is_consonant(verticality: Verticality) -> bool:
    return verticality.simple_semitones in CONSONANT_SIMPLE_SEMITONES


@dataclass(frozen=True)
class StrongBeatConsonanceRule:
    rule_id: str = "strong_beat_consonance"
    penalty: float = 12.0

    def evaluate(
        self,
        candidate: CanonCandidate,
        context: AnalysisContext,
    ) -> tuple[RuleViolation, ...]:
        del candidate
        return tuple(
            _violation_for_verticality(
                rule_id=self.rule_id,
                severity="hard",
                penalty=self.penalty,
                message="Accented vertical sonority must be consonant.",
                verticality=verticality,
            )
            for verticality in context.verticalities
            if verticality.beat_strength in {"strong", "medium"} and not is_consonant(verticality)
        )


@dataclass(frozen=True)
class WeakBeatDissonanceRule:
    rule_id: str = "weak_beat_dissonance"
    penalty: float = 2.0

    def evaluate(
        self,
        candidate: CanonCandidate,
        context: AnalysisContext,
    ) -> tuple[RuleViolation, ...]:
        del candidate
        return tuple(
            _violation_for_verticality(
                rule_id=self.rule_id,
                severity="soft",
                penalty=self.penalty,
                message="Weak-beat dissonance requires later repair or explanation.",
                verticality=verticality,
            )
            for verticality in context.verticalities
            if verticality.beat_strength == "weak" and not is_consonant(verticality)
        )


def _violation_for_verticality(
    *,
    rule_id: str,
    severity: str,
    penalty: float,
    message: str,
    verticality: Verticality,
) -> RuleViolation:
    return RuleViolation(
        rule_id=rule_id,
        severity=severity,  # pyright: ignore[reportArgumentType]
        penalty=penalty,
        message=message,
        bar=verticality.bar,
        beat=verticality.beat,
        voice_ids=tuple(sorted(verticality.pitches)),
        event_ids=tuple(sorted(verticality.event_ids.values())),
        data={
            "interval_name": verticality.interval_name,
            "simple_interval_name": verticality.simple_interval_name,
            "simple_semitones": verticality.simple_semitones,
        },
    )
