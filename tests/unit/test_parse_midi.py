from __future__ import annotations

from fractions import Fraction
from pathlib import Path

from kithairon.adapters.music21_parse import parse_melody
from tests.music_helpers import midi_score, write_score


def test_parse_midi_converts_notes_to_melody_events(tmp_path: Path) -> None:
    path = write_score(midi_score(), tmp_path / "melody.mid")

    melody = parse_melody(path)

    assert [event.pitch for event in melody.events] == [60, 64, 67]
    assert [event.start for event in melody.events] == [Fraction(0), Fraction(1), Fraction(2)]
    assert [event.duration for event in melody.events] == [Fraction(1), Fraction(1), Fraction(2)]
