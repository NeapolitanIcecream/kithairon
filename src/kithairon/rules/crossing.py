"""Voice-order and crossing rules."""

from __future__ import annotations

from dataclasses import dataclass

from kithairon.analysis import AnalysisContext, Verticality
from kithairon.ir import CanonCandidate, RuleViolation, VoiceName


@dataclass(frozen=True)
class VoiceCrossingRule:
    rule_id: str = "voice_crossing"
    penalty: float = 10.0

    def evaluate(
        self,
        candidate: CanonCandidate,
        context: AnalysisContext,
    ) -> tuple[RuleViolation, ...]:
        if len(candidate.voices) < 2:
            return ()

        first_voice = candidate.voices[0].name
        second_voice = candidate.voices[1].name
        return _detect_voice_crossings(
            context.verticalities,
            first_voice=first_voice,
            second_voice=second_voice,
            rule_id=self.rule_id,
            penalty=self.penalty,
        )


def _detect_voice_crossings(
    verticalities: tuple[Verticality, ...],
    *,
    first_voice: VoiceName,
    second_voice: VoiceName,
    rule_id: str,
    penalty: float,
) -> tuple[RuleViolation, ...]:
    violations: list[RuleViolation] = []
    previous_sign: int | None = None
    previous_verticality: Verticality | None = None

    for verticality in verticalities:
        if first_voice not in verticality.pitches or second_voice not in verticality.pitches:
            continue
        pitch_delta = verticality.pitches[first_voice] - verticality.pitches[second_voice]
        if pitch_delta == 0:
            continue
        current_sign = 1 if pitch_delta > 0 else -1
        if previous_sign is not None and current_sign != previous_sign:
            violations.append(
                RuleViolation(
                    rule_id=rule_id,
                    severity="hard",
                    penalty=penalty,
                    message="Voice order flips between adjacent verticalities.",
                    bar=verticality.bar,
                    beat=verticality.beat,
                    voice_ids=(first_voice, second_voice),
                    event_ids=tuple(sorted(verticality.event_ids.values())),
                    data={
                        "previous_start": (
                            str(previous_verticality.start) if previous_verticality else None
                        ),
                        "current_start": str(verticality.start),
                        "previous_pitch_delta_sign": previous_sign,
                        "current_pitch_delta_sign": current_sign,
                    },
                )
            )
        previous_sign = current_sign
        previous_verticality = verticality

    return tuple(violations)
