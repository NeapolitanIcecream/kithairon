from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import pytest

from kithairon.adapters.music21_parse import parse_melody, quarter_length_to_fraction
from kithairon.config import InputConfig
from kithairon.errors import ParseError
from tests.music_helpers import (
    chord_score,
    melody_score,
    overlapping_score,
    two_part_score,
    write_score,
)


def test_parse_musicxml_converts_notes_rests_and_metadata(tmp_path: Path) -> None:
    path = write_score(melody_score(), tmp_path / "melody.musicxml")

    melody = parse_melody(path)

    assert [event.pitch for event in melody.events] == [60, 62, None, 64]
    assert [event.start for event in melody.events] == [
        Fraction(0),
        Fraction(1),
        Fraction(2),
        Fraction(5, 2),
    ]
    assert [event.duration for event in melody.events] == [
        Fraction(1),
        Fraction(1),
        Fraction(1, 2),
        Fraction(1, 2),
    ]
    assert melody.time_signature == "3/4"
    assert melody.tempo_bpm == 90
    assert melody.key_hint == "C major"
    assert melody.source_path == str(path)


def test_chord_input_raises_by_default(tmp_path: Path) -> None:
    path = write_score(chord_score(), tmp_path / "chord.musicxml")

    with pytest.raises(ParseError) as raised:
        parse_melody(path)

    assert raised.value.to_diagnostic()["code"] == "chord_not_allowed"


def test_chord_policy_top_note_selects_highest_chord_pitch(tmp_path: Path) -> None:
    path = write_score(chord_score(), tmp_path / "chord.musicxml")

    melody = parse_melody(path, InputConfig(chord_policy="top_note"))

    assert [event.pitch for event in melody.events] == [64]


def test_overlapping_notes_raise_polyphonic_error(tmp_path: Path) -> None:
    path = write_score(overlapping_score(), tmp_path / "overlap.musicxml")

    with pytest.raises(ParseError) as raised:
        parse_melody(path)

    assert raised.value.to_diagnostic()["code"] == "polyphonic_input"


def test_explicit_part_policy_selects_requested_part(tmp_path: Path) -> None:
    path = write_score(two_part_score(), tmp_path / "parts.musicxml")

    melody = parse_melody(path, InputConfig(part_policy="explicit_index", part_index=1))

    assert [event.pitch for event in melody.events] == [67]


def test_highest_average_pitch_part_policy_selects_highest_part(tmp_path: Path) -> None:
    path = write_score(two_part_score(), tmp_path / "parts.musicxml")

    melody = parse_melody(path, InputConfig(part_policy="highest_average_pitch"))

    assert [event.pitch for event in melody.events] == [67]


def test_quantize_limits_fraction_denominator() -> None:
    quantized = quarter_length_to_fraction(0.333333333333, quantize=True, max_denominator=48)

    assert quantized == Fraction(1, 3)
