"""Time-sliced score analysis primitives."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from itertools import pairwise
from typing import Literal

from kithairon.ir import NoteEvent, Voice, VoiceName

type BeatStrength = Literal["strong", "medium", "weak"]


@dataclass(frozen=True)
class TimeSignatureInfo:
    numerator: int
    denominator: int
    beat_length: Fraction
    bar_length: Fraction


@dataclass(frozen=True)
class TimeSlice:
    start: Fraction
    end: Fraction
    bar: int
    beat: Fraction
    beat_strength: BeatStrength
    active_events: Mapping[VoiceName, NoteEvent]

    @property
    def duration(self) -> Fraction:
        return self.end - self.start


def parse_time_signature(time_signature: str) -> TimeSignatureInfo:
    """Parse simple meter strings such as ``4/4`` and ``3/4``."""
    try:
        numerator_text, denominator_text = time_signature.split("/", maxsplit=1)
        numerator = int(numerator_text)
        denominator = int(denominator_text)
    except ValueError as exc:
        raise ValueError(f"unsupported time signature: {time_signature!r}") from exc

    if numerator <= 0 or denominator <= 0:
        raise ValueError(f"unsupported time signature: {time_signature!r}")

    beat_length = Fraction(4, denominator)
    return TimeSignatureInfo(
        numerator=numerator,
        denominator=denominator,
        beat_length=beat_length,
        bar_length=numerator * beat_length,
    )


def build_time_slices(
    voices: tuple[Voice, ...],
    *,
    time_signature: str | None = None,
) -> tuple[TimeSlice, ...]:
    """Split the voice timeline wherever musical state or beat position changes."""
    if not voices:
        return ()

    meter = parse_time_signature(time_signature or voices[0].melody.time_signature)
    final_time = _final_time(voices)
    if final_time <= 0:
        return ()

    boundaries = _event_boundaries(voices) | _metric_boundaries(final_time, meter)
    ordered = sorted(boundary for boundary in boundaries if Fraction(0) <= boundary <= final_time)

    return tuple(
        TimeSlice(
            start=start,
            end=end,
            bar=_bar_for_offset(start, meter),
            beat=_beat_for_offset(start, meter),
            beat_strength=_beat_strength(start, meter),
            active_events=_active_events_at(voices, start),
        )
        for start, end in pairwise(ordered)
        if end > start
    )


def _final_time(voices: tuple[Voice, ...]) -> Fraction:
    return max(
        (event.start + event.duration for voice in voices for event in voice.melody.events),
        default=Fraction(0),
    )


def _event_boundaries(voices: tuple[Voice, ...]) -> set[Fraction]:
    boundaries: set[Fraction] = {Fraction(0)}
    for voice in voices:
        for event in voice.melody.events:
            boundaries.add(event.start)
            boundaries.add(event.start + event.duration)
    return boundaries


def _metric_boundaries(final_time: Fraction, meter: TimeSignatureInfo) -> set[Fraction]:
    boundaries: set[Fraction] = {Fraction(0), final_time}
    position = Fraction(0)
    while position < final_time:
        boundaries.add(position)
        position += meter.beat_length
    return boundaries


def _active_events_at(voices: tuple[Voice, ...], offset: Fraction) -> Mapping[VoiceName, NoteEvent]:
    active_events: dict[VoiceName, NoteEvent] = {}
    for voice in voices:
        for event in voice.melody.events:
            if event.start <= offset < event.start + event.duration:
                active_events[voice.name] = event
                break
    return active_events


def _bar_for_offset(offset: Fraction, meter: TimeSignatureInfo) -> int:
    return int(offset // meter.bar_length) + 1


def _beat_for_offset(offset: Fraction, meter: TimeSignatureInfo) -> Fraction:
    offset_in_bar = offset - ((offset // meter.bar_length) * meter.bar_length)
    return (offset_in_bar / meter.beat_length) + 1


def _beat_strength(offset: Fraction, meter: TimeSignatureInfo) -> BeatStrength:
    offset_in_bar = offset - ((offset // meter.bar_length) * meter.bar_length)
    if offset_in_bar == 0:
        return "strong"

    beat_index = offset_in_bar / meter.beat_length
    if beat_index.denominator == 1 and meter.numerator % 2 == 0:
        secondary_strong_index = Fraction(meter.numerator, 2)
        if beat_index == secondary_strong_index:
            return "medium"

    return "weak"
