"""Melodic motion rules for individual voices."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise

from kithairon.analysis import AnalysisContext
from kithairon.ir import CanonCandidate, NoteEvent, RuleViolation, Voice, VoiceName


@dataclass(frozen=True)
class PitchedEvent:
    event: NoteEvent
    pitch: int


@dataclass(frozen=True)
class LargeLeapRule:
    rule_id: str = "large_leap"
    max_semitones: int = 12
    penalty: float = 3.0

    def evaluate(
        self,
        candidate: CanonCandidate,
        context: AnalysisContext,
    ) -> tuple[RuleViolation, ...]:
        del context
        return tuple(
            violation
            for voice in candidate.voices
            for violation in self._violations_for_voice(voice)
        )

    def _violations_for_voice(self, voice: Voice) -> tuple[RuleViolation, ...]:
        pitched_events = tuple(
            PitchedEvent(event=event, pitch=event.pitch)
            for event in voice.melody.events
            if event.pitch is not None
        )
        return tuple(
            _violation_for_leap(
                rule_id=self.rule_id,
                penalty=self.penalty,
                voice_name=voice.name,
                previous=previous,
                current=current,
            )
            for previous, current in pairwise(pitched_events)
            if abs(current.pitch - previous.pitch) > self.max_semitones
        )


def _violation_for_leap(
    *,
    rule_id: str,
    penalty: float,
    voice_name: VoiceName,
    previous: PitchedEvent,
    current: PitchedEvent,
) -> RuleViolation:
    leap = current.pitch - previous.pitch
    return RuleViolation(
        rule_id=rule_id,
        severity="soft",
        penalty=penalty,
        message="Melodic leap is larger than the configured limit.",
        voice_ids=(voice_name,),
        event_ids=(previous.event.id, current.event.id),
        data={
            "leap_semitones": leap,
            "absolute_leap_semitones": abs(leap),
        },
    )
