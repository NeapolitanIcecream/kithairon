"""Phrase-span analysis for composition assistance."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from kithairon.analysis.timeline import parse_time_signature
from kithairon.ir import CanonCandidate, NoteEvent, Voice


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
        start = min(event.start for _, event in phrase_events)
        end = max(event.start + event.duration for _, event in phrase_events)
        phrases.append(
            PhraseSpan(
                phrase_id=f"phrase-{index:02d}",
                bar_start=bar_start,
                bar_end=bar_end,
                start=start,
                end=end,
                event_ids=tuple(_event_ref(voice, event) for voice, event in phrase_events),
                note_count=len(phrase_events),
                label=f"Bars {bar_start}-{bar_end}",
            )
        )
    return tuple(phrases)


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
