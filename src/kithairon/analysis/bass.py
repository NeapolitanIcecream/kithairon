"""Bass-support analysis for composition assistance."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import pairwise
from typing import Literal

from kithairon.analysis.timeline import parse_time_signature
from kithairon.ir import CanonCandidate, NoteEvent, Voice

type BassMotionLabel = Literal["static", "stepwise", "active"]


@dataclass(frozen=True)
class BassSupportSummary:
    voice_id: str
    bar_start: int
    bar_end: int
    unique_pitch_count: int
    repeated_note_ratio: float
    stepwise_motion_ratio: float
    average_abs_motion: float
    static_bars: tuple[int, ...]
    static_bass: bool
    motion_label: BassMotionLabel


def summarize_bass_support(candidate: CanonCandidate) -> BassSupportSummary | None:
    """Summarize bass motion over the candidate timeline."""
    bass_voice = _bass_voice(candidate)
    if bass_voice is None:
        return None

    events = tuple(event for event in bass_voice.melody.events if event.pitch is not None)
    if not events:
        return None

    meter = parse_time_signature(bass_voice.melody.time_signature)
    intervals = _intervals(events)
    repeated_ratio = _ratio(sum(1 for interval in intervals if interval == 0), len(intervals))
    stepwise_ratio = _ratio(
        sum(1 for interval in intervals if 0 < abs(interval) <= 2),
        len(intervals),
    )
    average_motion = (
        sum(abs(interval) for interval in intervals) / len(intervals) if intervals else 0.0
    )
    unique_pitch_count = len({event.pitch for event in events})
    static_bass = repeated_ratio >= 0.5 or unique_pitch_count <= 1
    return BassSupportSummary(
        voice_id=bass_voice.name,
        bar_start=_bar_for_event(events[0], meter.bar_length),
        bar_end=_bar_for_event(events[-1], meter.bar_length),
        unique_pitch_count=unique_pitch_count,
        repeated_note_ratio=round(repeated_ratio, 4),
        stepwise_motion_ratio=round(stepwise_ratio, 4),
        average_abs_motion=round(average_motion, 4),
        static_bars=_static_bars(events, meter.bar_length),
        static_bass=static_bass,
        motion_label=_motion_label(static_bass, stepwise_ratio),
    )


def _bass_voice(candidate: CanonCandidate) -> Voice | None:
    follower = next((voice for voice in candidate.voices if voice.role == "follower"), None)
    if follower is not None:
        return follower
    pitched_voices = [
        voice
        for voice in candidate.voices
        if any(event.pitch is not None for event in voice.melody.events)
    ]
    return min(pitched_voices, key=_average_pitch, default=None)


def _average_pitch(voice: Voice) -> float:
    pitches = [event.pitch for event in voice.melody.events if event.pitch is not None]
    return sum(pitches) / len(pitches) if pitches else float("inf")


def _intervals(events: tuple[NoteEvent, ...]) -> tuple[int, ...]:
    intervals: list[int] = []
    for previous, current in pairwise(events):
        if previous.pitch is not None and current.pitch is not None:
            intervals.append(current.pitch - previous.pitch)
    return tuple(intervals)


def _static_bars(events: tuple[NoteEvent, ...], bar_length: Fraction) -> tuple[int, ...]:
    bars: list[int] = []
    for previous, current in pairwise(events):
        if previous.pitch == current.pitch:
            bar = _bar_for_event(current, bar_length)
            if bar not in bars:
                bars.append(bar)
    return tuple(bars)


def _bar_for_event(event: NoteEvent, bar_length: Fraction) -> int:
    return int(event.start // bar_length) + 1


def _ratio(count: int, total: int) -> float:
    return count / total if total > 0 else 0.0


def _motion_label(static_bass: bool, stepwise_ratio: float) -> BassMotionLabel:
    if static_bass:
        return "static"
    if stepwise_ratio >= 0.6:
        return "stepwise"
    return "active"
