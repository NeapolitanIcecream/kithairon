"""Phrase-span analysis for composition assistance."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import groupby
from typing import Literal

from kithairon.analysis.timeline import parse_time_signature
from kithairon.ir import CanonCandidate, NoteEvent, Voice

type PhraseWarningKind = Literal["repeated_note_plateau", "flat_sequence"]
type PhraseWarningVoiceRole = Literal["leader", "follower", "both", "unknown"]


@dataclass(frozen=True)
class PhraseWarning:
    kind: PhraseWarningKind
    voice_role: PhraseWarningVoiceRole
    event_ids: tuple[str, ...]
    message: str


@dataclass(frozen=True)
class PhraseSpan:
    phrase_id: str
    bar_start: int
    bar_end: int
    start: Fraction
    end: Fraction
    event_ids: tuple[str, ...]
    note_count: int
    label: str
    high_point_event_id: str | None
    high_point_pitch: int | None
    arrival_event_id: str | None
    arrival_pitch: int | None
    repeated_note_plateaus: tuple[str, ...]
    flat_sequence_warning: bool
    warnings: tuple[str, ...]
    warning_items: tuple[PhraseWarning, ...]


def build_phrase_spans(
    candidate: CanonCandidate,
    *,
    bars_per_phrase: int = 2,
) -> tuple[PhraseSpan, ...]:
    """Group candidate notes into stable metric phrase spans."""
    if bars_per_phrase < 1:
        raise ValueError("bars_per_phrase must be positive")
    events = _pitched_voice_events(candidate)
    if not events:
        return ()

    meter = parse_time_signature(candidate.voices[0].melody.time_signature)
    final_bar = max(_bar_for_event(event, meter.bar_length) for _, event in events)
    phrases: list[PhraseSpan] = []
    for index, bar_start in enumerate(range(1, final_bar + 1, bars_per_phrase), start=1):
        bar_end = min(final_bar, bar_start + bars_per_phrase - 1)
        phrase_events = tuple(
            (voice, event)
            for voice, event in events
            if bar_start <= _bar_for_event(event, meter.bar_length) <= bar_end
        )
        if not phrase_events:
            continue
        phrases.append(
            _phrase_span(
                index=index,
                bar_start=bar_start,
                bar_end=bar_end,
                phrase_events=phrase_events,
            )
        )
    return tuple(phrases)


def _phrase_span(
    *,
    index: int,
    bar_start: int,
    bar_end: int,
    phrase_events: tuple[tuple[Voice, NoteEvent], ...],
) -> PhraseSpan:
    start = min(event.start for _, event in phrase_events)
    end = max(event.start + event.duration for _, event in phrase_events)
    high_point = _high_point(phrase_events)
    arrival = _arrival(phrase_events)
    warning_items = _warning_items(phrase_events)
    repeated_note_plateaus = tuple(
        event_id
        for warning in warning_items
        if warning.kind == "repeated_note_plateau"
        for event_id in warning.event_ids
    )
    flat_sequence_warning = any(warning.kind == "flat_sequence" for warning in warning_items)
    warnings = tuple(dict.fromkeys(warning.kind for warning in warning_items))
    return PhraseSpan(
        phrase_id=f"phrase-{index:02d}",
        bar_start=bar_start,
        bar_end=bar_end,
        start=start,
        end=end,
        event_ids=tuple(_event_ref(voice, event) for voice, event in phrase_events),
        note_count=len(phrase_events),
        label=f"Bars {bar_start}-{bar_end}",
        high_point_event_id=_event_ref(*high_point),
        high_point_pitch=high_point[1].pitch,
        arrival_event_id=_event_ref(*arrival),
        arrival_pitch=arrival[1].pitch,
        repeated_note_plateaus=repeated_note_plateaus,
        flat_sequence_warning=flat_sequence_warning,
        warnings=warnings,
        warning_items=warning_items,
    )


def _pitched_voice_events(candidate: CanonCandidate) -> tuple[tuple[Voice, NoteEvent], ...]:
    return tuple(
        (voice, event)
        for voice in candidate.voices
        for event in voice.melody.events
        if event.pitch is not None
    )


def _bar_for_event(event: NoteEvent, bar_length: Fraction) -> int:
    return int(event.start // bar_length) + 1


def _event_ref(voice: Voice, event: NoteEvent) -> str:
    return f"{voice.name}:{event.id}"


def _high_point(events: tuple[tuple[Voice, NoteEvent], ...]) -> tuple[Voice, NoteEvent]:
    return max(events, key=lambda item: (item[1].pitch or -1, item[1].start, item[0].name))


def _arrival(events: tuple[tuple[Voice, NoteEvent], ...]) -> tuple[Voice, NoteEvent]:
    return max(
        events,
        key=lambda item: (
            item[1].start + item[1].duration,
            item[1].start,
            item[1].pitch or -1,
            item[0].name,
        ),
    )


def _warning_items(events: tuple[tuple[Voice, NoteEvent], ...]) -> tuple[PhraseWarning, ...]:
    warnings: list[PhraseWarning] = []
    for voice, voice_events in _events_by_voice(events).items():
        for _, group in groupby(voice_events, key=lambda event: event.pitch):
            repeated = tuple(group)
            if len(repeated) >= 3:
                event_ids = tuple(_event_ref(voice, event) for event in repeated)
                warnings.append(
                    PhraseWarning(
                        kind="repeated_note_plateau",
                        voice_role=voice.role,
                        event_ids=event_ids,
                        message=(
                            f"{_voice_label(voice.role)} repeats one pitch across "
                            f"{len(repeated)} notes."
                        ),
                    )
                )
        if _flat_sequence_warning_for_voice(voice_events):
            warnings.append(
                PhraseWarning(
                    kind="flat_sequence",
                    voice_role=voice.role,
                    event_ids=tuple(_event_ref(voice, event) for event in voice_events),
                    message=f"{_voice_label(voice.role)} stays within a narrow pitch band.",
                )
            )
    return tuple(warnings)


def _flat_sequence_warning_for_voice(voice_events: tuple[NoteEvent, ...]) -> bool:
    if len(voice_events) < 4:
        return False
    pitches = [event.pitch for event in voice_events if event.pitch is not None]
    return bool(pitches and max(pitches) - min(pitches) <= 2 and len(set(pitches)) <= 2)


def _voice_label(role: PhraseWarningVoiceRole) -> str:
    if role == "leader":
        return "Upper voice"
    if role == "follower":
        return "Lower voice"
    return "Phrase"


def _events_by_voice(
    events: tuple[tuple[Voice, NoteEvent], ...],
) -> dict[Voice, tuple[NoteEvent, ...]]:
    grouped: dict[Voice, list[NoteEvent]] = {}
    for voice, event in events:
        grouped.setdefault(voice, []).append(event)
    return {
        voice: tuple(sorted(voice_events, key=lambda event: (event.start, event.id)))
        for voice, voice_events in grouped.items()
    }
