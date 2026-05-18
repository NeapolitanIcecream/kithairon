"""Register and pitch-range rules."""

from __future__ import annotations

from dataclasses import dataclass

from kithairon.analysis import AnalysisContext
from kithairon.ir import CanonCandidate, RuleViolation, Voice, VoiceName

RangeBounds = tuple[int, int]


@dataclass(frozen=True)
class RangeRule:
    rule_id: str = "range"
    lower_voice_range: RangeBounds = (36, 76)
    upper_voice_range: RangeBounds = (55, 88)
    penalty: float = 4.0

    def evaluate(
        self,
        candidate: CanonCandidate,
        context: AnalysisContext,
    ) -> tuple[RuleViolation, ...]:
        del context
        role_by_voice = _classify_registers(candidate.voices)
        return tuple(
            violation
            for voice in candidate.voices
            for violation in self._violations_for_voice(
                voice,
                bounds=(
                    self.upper_voice_range
                    if role_by_voice.get(voice.name) == "upper"
                    else self.lower_voice_range
                ),
            )
        )

    def _violations_for_voice(
        self,
        voice: Voice,
        *,
        bounds: RangeBounds,
    ) -> tuple[RuleViolation, ...]:
        lower_bound, upper_bound = bounds
        return tuple(
            RuleViolation(
                rule_id=self.rule_id,
                severity="soft",
                penalty=self.penalty,
                message="Pitch falls outside the configured register range.",
                voice_ids=(voice.name,),
                event_ids=(event.id,),
                data={
                    "pitch": event.pitch,
                    "lower_bound": lower_bound,
                    "upper_bound": upper_bound,
                },
            )
            for event in voice.melody.events
            if event.pitch is not None and not lower_bound <= event.pitch <= upper_bound
        )


def _classify_registers(voices: tuple[Voice, ...]) -> dict[VoiceName, str]:
    averages = {
        voice.name: _average_pitch(voice) for voice in voices if _average_pitch(voice) is not None
    }
    if not averages:
        return {}

    upper_voice = max(averages.items(), key=lambda item: (item[1], item[0]))[0]
    return {voice.name: ("upper" if voice.name == upper_voice else "lower") for voice in voices}


def _average_pitch(voice: Voice) -> float | None:
    pitches = [event.pitch for event in voice.melody.events if event.pitch is not None]
    if not pitches:
        return None
    return sum(pitches) / len(pitches)
