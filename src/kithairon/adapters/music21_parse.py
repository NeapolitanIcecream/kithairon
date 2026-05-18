"""Parse MIDI and MusicXML inputs into Kithairon melody IR."""

from __future__ import annotations

from collections.abc import Iterable
from fractions import Fraction
from pathlib import Path
from typing import Any, cast

from music21 import chord as music21_chord
from music21 import converter as music21_converter
from music21 import key as music21_key
from music21 import meter as music21_meter
from music21 import note as music21_note
from music21 import tempo as music21_tempo

from kithairon.config import ChordPolicy, InputConfig
from kithairon.errors import ParseError
from kithairon.ir import Melody, NoteEvent, TieType

SUPPORTED_INPUT_SUFFIXES = {".mid", ".midi", ".musicxml", ".xml", ".mxl"}


def parse_melody(path: str | Path, config: InputConfig | None = None) -> Melody:
    """Read a MIDI or MusicXML file and return a monophonic melody."""
    source_path = Path(path)
    input_config = InputConfig() if config is None else config
    _ensure_supported_path(source_path)

    try:
        score = cast(Any, music21_converter).parse(str(source_path))
    except Exception as exc:
        raise ParseError(
            f"Could not parse input score: {source_path}",
            code="parse_failed",
            details={"path": str(source_path), "error": str(exc)},
        ) from exc

    selected_part = select_part(score, input_config)
    events = tuple(_iter_note_events(selected_part, input_config))
    if not events:
        raise ParseError(
            f"Input score does not contain any notes or rests: {source_path}",
            code="empty_melody",
            details={"path": str(source_path)},
        )

    _ensure_monophonic(events, source_path)
    return Melody(
        events=events,
        time_signature=_read_time_signature(selected_part, score),
        tempo_bpm=_read_tempo_bpm(selected_part, score),
        key_hint=_read_key_hint(selected_part, score),
        source_path=str(source_path),
    )


def select_part(score: Any, config: InputConfig) -> Any:
    parts = _score_parts(score)
    if not parts:
        return score

    if config.part_policy == "first":
        return parts[0]
    if config.part_policy == "explicit_index":
        if config.part_index >= len(parts):
            raise ParseError(
                f"Requested part index {config.part_index} but score has {len(parts)} parts.",
                code="part_index_out_of_range",
                details={"part_index": config.part_index, "part_count": len(parts)},
            )
        return parts[config.part_index]
    if config.part_policy == "highest_average_pitch":
        return max(parts, key=lambda part: _average_pitch(part, config.chord_policy))

    raise ParseError(
        f"Unsupported part policy: {config.part_policy}",
        code="unsupported_part_policy",
        details={"part_policy": config.part_policy},
    )


def quarter_length_to_fraction(
    value: object,
    *,
    quantize: bool,
    max_denominator: int,
) -> Fraction:
    if isinstance(value, Fraction):
        parsed = value
    elif isinstance(value, int):
        parsed = Fraction(value, 1)
    elif isinstance(value, float):
        parsed = Fraction(str(value))
    else:
        parsed = Fraction(str(value))

    if quantize:
        return parsed.limit_denominator(max_denominator)
    return parsed


def _ensure_supported_path(path: Path) -> None:
    if path.suffix.lower() not in SUPPORTED_INPUT_SUFFIXES:
        raise ParseError(
            f"Unsupported input format: {path.suffix or '<none>'}",
            code="unsupported_input_format",
            details={"path": str(path), "suffix": path.suffix.lower()},
        )


def _score_parts(score: Any) -> list[Any]:
    parts = getattr(score, "parts", None)
    if parts is None:
        return []
    return list(cast(Iterable[Any], parts))


def _iter_note_events(part: Any, config: InputConfig) -> Iterable[NoteEvent]:
    flattened = part.flatten()
    elements = cast(Iterable[Any], flattened.notesAndRests)
    for index, element in enumerate(elements, start=1):
        pitch = _element_pitch(element, config.chord_policy)
        start = quarter_length_to_fraction(
            element.offset,
            quantize=config.quantize,
            max_denominator=config.max_denominator,
        )
        duration = quarter_length_to_fraction(
            element.quarterLength,
            quantize=config.quantize,
            max_denominator=config.max_denominator,
        )
        yield NoteEvent(
            id=f"n{index:04d}",
            pitch=pitch,
            start=start,
            duration=duration,
            velocity=_velocity(element),
            tie=_tie_type(element),
        )


def _element_pitch(element: Any, chord_policy: ChordPolicy) -> int | None:
    if isinstance(element, music21_note.Rest):
        return None
    if isinstance(element, music21_note.Note):
        return _pitch_midi(cast(Any, element).pitch)
    if isinstance(element, music21_chord.Chord):
        pitches = list(cast(Iterable[Any], element.pitches))
        if not pitches:
            return None
        if chord_policy == "error":
            raise ParseError(
                "Chord input is not monophonic. Set chord_policy to top_note or bottom_note.",
                code="chord_not_allowed",
                details={"offset": str(element.offset), "pitch_count": len(pitches)},
            )

        def key_func(pitch: Any) -> int:
            return _pitch_midi(pitch)

        selected = (
            max(pitches, key=key_func) if chord_policy == "top_note" else min(pitches, key=key_func)
        )
        return _pitch_midi(selected)
    return None


def _velocity(element: Any) -> int:
    volume = getattr(element, "volume", None)
    velocity = getattr(volume, "velocity", None)
    if velocity is None:
        return 64
    return int(velocity)


def _pitch_midi(pitch: Any) -> int:
    return int(pitch.midi)


def _tie_type(element: Any) -> TieType | None:
    tie = getattr(element, "tie", None)
    tie_type = getattr(tie, "type", None)
    if tie_type in {"start", "continue", "stop"}:
        return cast(TieType, tie_type)
    return None


def _ensure_monophonic(events: tuple[NoteEvent, ...], source_path: Path) -> None:
    previous_end: Fraction | None = None
    previous_id: str | None = None
    notes = sorted(
        (event for event in events if event.pitch is not None), key=lambda item: item.start
    )
    for event in notes:
        if previous_end is not None and event.start < previous_end:
            raise ParseError(
                "Input score contains overlapping notes and is not monophonic.",
                code="polyphonic_input",
                details={
                    "path": str(source_path),
                    "event_id": event.id,
                    "previous_event_id": previous_id or "",
                    "start": str(event.start),
                    "previous_end": str(previous_end),
                },
            )
        previous_end = event.start + event.duration
        previous_id = event.id


def _average_pitch(part: Any, chord_policy: ChordPolicy) -> float:
    pitches: list[int] = []
    for element in cast(Iterable[Any], part.flatten().notes):
        if isinstance(element, music21_note.Note):
            pitches.append(_pitch_midi(cast(Any, element).pitch))
        elif isinstance(element, music21_chord.Chord):
            chord_pitches = list(cast(Iterable[Any], element.pitches))
            if chord_pitches:
                if chord_policy == "bottom_note":
                    pitches.append(min(_pitch_midi(pitch) for pitch in chord_pitches))
                else:
                    pitches.append(max(_pitch_midi(pitch) for pitch in chord_pitches))
    if not pitches:
        return float("-inf")
    return sum(pitches) / len(pitches)


def _read_time_signature(part: Any, score: Any) -> str:
    signature = _first_recurse_element(part, music21_meter.TimeSignature) or _first_recurse_element(
        score,
        music21_meter.TimeSignature,
    )
    if signature is None:
        return "4/4"
    return str(signature.ratioString)


def _read_tempo_bpm(part: Any, score: Any) -> int | None:
    mark = _first_recurse_element(part, music21_tempo.MetronomeMark) or _first_recurse_element(
        score,
        music21_tempo.MetronomeMark,
    )
    if mark is None or mark.number is None:
        return None
    return round(float(mark.number))


def _read_key_hint(part: Any, score: Any) -> str | None:
    key_obj = _first_recurse_element(part, music21_key.Key) or _first_recurse_element(
        score,
        music21_key.Key,
    )
    if key_obj is not None:
        return f"{key_obj.tonic.name} {key_obj.mode}"

    key_signature = _first_recurse_element(
        part, music21_key.KeySignature
    ) or _first_recurse_element(
        score,
        music21_key.KeySignature,
    )
    if key_signature is None:
        return None
    sharps = int(key_signature.sharps)
    return f"{sharps:+d} sharps"


def _first_recurse_element(stream_obj: Any, class_filter: object) -> Any | None:
    elements = list(cast(Iterable[Any], stream_obj.recurse().getElementsByClass(class_filter)))
    if not elements:
        return None
    return elements[0]
