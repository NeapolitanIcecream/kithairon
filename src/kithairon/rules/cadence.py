"""Cadential stability checks."""

from __future__ import annotations

from dataclasses import dataclass

from kithairon.analysis import AnalysisContext, Verticality
from kithairon.ir import CanonCandidate, RuleViolation

CADENTIAL_CONSONANCES = frozenset({0, 3, 4, 7, 8, 9})


@dataclass(frozen=True)
class CadenceStabilityRule:
    rule_id: str = "cadence_stability"
    penalty: float = 6.0

    def evaluate(
        self,
        candidate: CanonCandidate,
        context: AnalysisContext,
    ) -> tuple[RuleViolation, ...]:
        del candidate
        if not context.verticalities:
            return ()

        final_verticality = context.verticalities[-1]
        if final_verticality.simple_semitones in CADENTIAL_CONSONANCES:
            return ()
        return (_violation_for_final_verticality(self.rule_id, self.penalty, final_verticality),)


def _violation_for_final_verticality(
    rule_id: str,
    penalty: float,
    verticality: Verticality,
) -> RuleViolation:
    return RuleViolation(
        rule_id=rule_id,
        severity="soft",
        penalty=penalty,
        message="Final vertical sonority should resolve to a cadential consonance.",
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
