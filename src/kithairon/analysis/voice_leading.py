"""Voice-leading quartet analysis."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from itertools import pairwise
from typing import Any

from music21 import note, voiceLeading

from kithairon.analysis.verticality import Verticality
from kithairon.ir import VoiceName


@dataclass(frozen=True)
class VoiceLeadingQuartetAnalysis:
    start: Fraction
    end: Fraction
    bar: int
    beat: Fraction
    voice_names: tuple[VoiceName, VoiceName]
    previous_pitches: Mapping[VoiceName, int]
    current_pitches: Mapping[VoiceName, int]
    previous_event_ids: Mapping[VoiceName, str]
    current_event_ids: Mapping[VoiceName, str]
    motion_type: str
    parallel_fifth: bool
    parallel_octave: bool
    parallel_unison: bool
    hidden_fifth: bool
    hidden_octave: bool


def build_voice_leading_quartets(
    verticalities: tuple[Verticality, ...],
) -> tuple[VoiceLeadingQuartetAnalysis, ...]:
    """Build adjacent two-voice quartets when both voices keep sounding pitches."""
    quartets: list[VoiceLeadingQuartetAnalysis] = []
    for previous, current in pairwise(verticalities):
        common_voice_names = tuple(sorted(set(previous.pitches) & set(current.pitches)))
        if len(common_voice_names) != 2:
            continue
        quartets.append(_quartet_analysis(previous, current, common_voice_names))
    return tuple(quartets)


def _quartet_analysis(
    previous: Verticality,
    current: Verticality,
    voice_names: tuple[VoiceName, VoiceName],
) -> VoiceLeadingQuartetAnalysis:
    first_voice, second_voice = voice_names
    quartet = voiceLeading.VoiceLeadingQuartet(
        _note_from_midi(previous.pitches[first_voice]),
        _note_from_midi(current.pitches[first_voice]),
        _note_from_midi(previous.pitches[second_voice]),
        _note_from_midi(current.pitches[second_voice]),
    )

    return VoiceLeadingQuartetAnalysis(
        start=previous.start,
        end=current.start,
        bar=current.bar,
        beat=current.beat,
        voice_names=voice_names,
        previous_pitches={voice_name: previous.pitches[voice_name] for voice_name in voice_names},
        current_pitches={voice_name: current.pitches[voice_name] for voice_name in voice_names},
        previous_event_ids={
            voice_name: previous.event_ids[voice_name] for voice_name in voice_names
        },
        current_event_ids={voice_name: current.event_ids[voice_name] for voice_name in voice_names},
        motion_type=_motion_type(quartet),
        parallel_fifth=bool(quartet.parallelFifth()),
        parallel_octave=bool(quartet.parallelOctave()),
        parallel_unison=bool(quartet.parallelUnison()),
        hidden_fifth=bool(quartet.hiddenFifth()),
        hidden_octave=bool(quartet.hiddenOctave()),
    )


def _note_from_midi(midi_pitch: int) -> Any:
    built_note: Any = note.Note()
    built_note.pitch.midi = midi_pitch
    return built_note


def _motion_type(quartet: Any) -> str:
    motion_type = str(quartet.motionType())
    return motion_type.removeprefix("MotionType.")
