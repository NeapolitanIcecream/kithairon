"""Bass-support analysis for composition assistance."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import pairwise
from typing import Literal

from kithairon.analysis.timeline import build_time_slices, parse_time_signature
from kithairon.analysis.verticality import build_verticalities
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
    strong_beat_support_event_ids: tuple[str, ...]
    root_support_proxy: float
    sustained_foundation_score: float
    bass_independence_score: float


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
    strong_beat_support_event_ids = _strong_beat_support_event_ids(
        bass_voice,
        events,
        meter.bar_length,
    )
    root_support_proxy = _root_support_proxy(candidate, bass_voice, strong_beat_support_event_ids)
    sustained_foundation_score = _sustained_foundation_score(events, meter.beat_length)
    bass_independence_score = _bass_independence_score(
        repeated_ratio,
        stepwise_ratio,
        unique_pitch_count,
        len(events),
    )
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
        strong_beat_support_event_ids=strong_beat_support_event_ids,
        root_support_proxy=root_support_proxy,
        sustained_foundation_score=sustained_foundation_score,
        bass_independence_score=bass_independence_score,
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


def _strong_beat_support_event_ids(
    bass_voice: Voice,
    events: tuple[NoteEvent, ...],
    bar_length: Fraction,
) -> tuple[str, ...]:
    return tuple(
        f"{bass_voice.name}:{event.id}" for event in events if event.start % bar_length == 0
    )


def _root_support_proxy(
    candidate: CanonCandidate,
    bass_voice: Voice,
    support_event_ids: tuple[str, ...],
) -> float:
    if not support_event_ids:
        return 0.0
    support_ids = {event_id.split(":", maxsplit=1)[1] for event_id in support_event_ids}
    verticalities = build_verticalities(
        build_time_slices(candidate.voices, time_signature=bass_voice.melody.time_signature)
    )
    supported = 0
    for verticality in verticalities:
        if verticality.beat_strength != "strong":
            continue
        if verticality.lower_voice != bass_voice.name:
            continue
        if verticality.event_ids.get(bass_voice.name) not in support_ids:
            continue
        if verticality.simple_interval_name in {"P1", "P5", "P8", "m3", "M3", "m6", "M6"}:
            supported += 1
    return round(supported / len(support_event_ids), 4)


def _sustained_foundation_score(
    events: tuple[NoteEvent, ...],
    beat_length: Fraction,
) -> float:
    total_duration = sum((event.duration for event in events), start=Fraction(0))
    if total_duration <= 0:
        return 0.0
    sustained = sum(
        (event.duration for event in events if event.duration >= beat_length),
        start=Fraction(0),
    )
    return round(float(sustained / total_duration), 4)


def _bass_independence_score(
    repeated_ratio: float,
    stepwise_ratio: float,
    unique_pitch_count: int,
    event_count: int,
) -> float:
    unique_ratio = unique_pitch_count / event_count if event_count > 0 else 0.0
    score = (1.0 - repeated_ratio) * 0.45 + stepwise_ratio * 0.25 + unique_ratio * 0.3 + 0.2
    return round(min(1.0, max(0.0, score)), 4)


def _ratio(count: int, total: int) -> float:
    return count / total if total > 0 else 0.0


def _motion_label(static_bass: bool, stepwise_ratio: float) -> BassMotionLabel:
    if static_bass:
        return "static"
    if stepwise_ratio >= 0.6:
        return "stepwise"
    return "active"
