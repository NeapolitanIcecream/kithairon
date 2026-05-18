"""Parallel perfect interval rules."""

from __future__ import annotations

from dataclasses import dataclass

from kithairon.analysis import AnalysisContext
from kithairon.analysis.voice_leading import VoiceLeadingQuartetAnalysis
from kithairon.ir import CanonCandidate, RuleViolation


@dataclass(frozen=True)
class ParallelPerfectRule:
    rule_id: str = "parallel_perfect"
    penalty: float = 14.0

    def evaluate(
        self,
        candidate: CanonCandidate,
        context: AnalysisContext,
    ) -> tuple[RuleViolation, ...]:
        del candidate
        return tuple(
            _violation_for_quartet(self.rule_id, self.penalty, quartet)
            for quartet in context.voice_leadings
            if quartet.parallel_fifth or quartet.parallel_octave or quartet.parallel_unison
        )


def _violation_for_quartet(
    rule_id: str,
    penalty: float,
    quartet: VoiceLeadingQuartetAnalysis,
) -> RuleViolation:
    parallel_types: list[str] = []
    if quartet.parallel_fifth:
        parallel_types.append("fifth")
    if quartet.parallel_octave:
        parallel_types.append("octave")
    if quartet.parallel_unison:
        parallel_types.append("unison")

    event_ids = tuple(
        sorted(set(quartet.previous_event_ids.values()) | set(quartet.current_event_ids.values()))
    )
    return RuleViolation(
        rule_id=rule_id,
        severity="hard",
        penalty=penalty,
        message=f"Parallel perfect {'/'.join(parallel_types)} detected.",
        bar=quartet.bar,
        beat=quartet.beat,
        voice_ids=quartet.voice_names,
        event_ids=event_ids,
        data={
            "parallel_types": tuple(parallel_types),
            "motion_type": quartet.motion_type,
            "previous_pitches": dict(quartet.previous_pitches),
            "current_pitches": dict(quartet.current_pitches),
        },
    )
