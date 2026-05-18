"""Vertical interval analysis for two-voice candidates."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from music21 import interval, pitch

from kithairon.analysis.timeline import BeatStrength, TimeSlice
from kithairon.ir import NoteEvent, VoiceName


@dataclass(frozen=True)
class Verticality:
    start: Fraction
    end: Fraction
    bar: int
    beat: Fraction
    beat_strength: BeatStrength
    pitches: Mapping[VoiceName, int]
    event_ids: Mapping[VoiceName, str]
    lower_voice: VoiceName
    upper_voice: VoiceName
    semitones: int
    simple_semitones: int
    interval_name: str
    simple_interval_name: str


def build_verticalities(time_slices: tuple[TimeSlice, ...]) -> tuple[Verticality, ...]:
    """Return vertical intervals for slices with at least two sounding pitches."""
    return tuple(
        verticality
        for time_slice in time_slices
        if (verticality := _verticality_for_slice(time_slice)) is not None
    )


def _verticality_for_slice(time_slice: TimeSlice) -> Verticality | None:
    pitched_events: dict[VoiceName, tuple[NoteEvent, int]] = {}
    for voice_name, event in time_slice.active_events.items():
        if event.pitch is not None:
            pitched_events[voice_name] = (event, event.pitch)

    if len(pitched_events) < 2:
        return None

    pitch_items = tuple(
        (voice_name, pitch_value) for voice_name, (_, pitch_value) in pitched_events.items()
    )
    lower_voice, lower_pitch = min(pitch_items, key=lambda item: (item[1], item[0]))
    upper_voice, upper_pitch = max(pitch_items, key=lambda item: (item[1], item[0]))
    semitones = upper_pitch - lower_pitch
    interval_obj = _music21_interval(lower_pitch, upper_pitch)

    return Verticality(
        start=time_slice.start,
        end=time_slice.end,
        bar=time_slice.bar,
        beat=time_slice.beat,
        beat_strength=time_slice.beat_strength,
        pitches={voice_name: pitch_value for voice_name, pitch_value in pitch_items},
        event_ids={voice_name: event.id for voice_name, (event, _) in pitched_events.items()},
        lower_voice=lower_voice,
        upper_voice=upper_voice,
        semitones=semitones,
        simple_semitones=semitones % 12,
        interval_name=str(interval_obj.name),
        simple_interval_name=str(interval_obj.simpleName),
    )


def _music21_interval(lower_midi: int, upper_midi: int) -> Any:
    lower_pitch = pitch.Pitch()
    lower_pitch.midi = lower_midi
    upper_pitch = pitch.Pitch()
    upper_pitch.midi = upper_midi
    return interval.Interval(lower_pitch, upper_pitch)
