# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false

from __future__ import annotations

from pathlib import Path
from typing import Any

from music21 import chord, key, meter, note, stream, tempo


def melody_score() -> Any:
    score = stream.Score()
    part = stream.Part()
    part.insert(0, meter.TimeSignature("3/4"))
    part.insert(0, tempo.MetronomeMark(number=90))
    part.insert(0, key.Key("C"))

    part.insert(0, note.Note("C4", quarterLength=1))
    part.insert(1, note.Note("D4", quarterLength=1))
    part.insert(2, note.Rest(quarterLength=0.5))
    part.insert(2.5, note.Note("E4", quarterLength=0.5))
    score.insert(0, part)
    return score


def midi_score() -> Any:
    score = stream.Score()
    part = stream.Part()
    part.insert(0, meter.TimeSignature("4/4"))
    part.insert(0, tempo.MetronomeMark(number=100))
    part.insert(0, note.Note("C4", quarterLength=1))
    part.insert(1, note.Note("E4", quarterLength=1))
    part.insert(2, note.Note("G4", quarterLength=2))
    score.insert(0, part)
    return score


def chord_score() -> Any:
    score = stream.Score()
    part = stream.Part()
    part.insert(0, meter.TimeSignature("4/4"))
    part.insert(0, chord.Chord(["C4", "E4"], quarterLength=1))
    score.insert(0, part)
    return score


def overlapping_score() -> Any:
    score = stream.Score()
    part = stream.Part()
    part.insert(0, meter.TimeSignature("4/4"))
    part.insert(0, note.Note("C4", quarterLength=2))
    part.insert(1, note.Note("D4", quarterLength=1))
    score.insert(0, part)
    return score


def two_part_score() -> Any:
    score = stream.Score()
    lower = stream.Part()
    upper = stream.Part()
    lower.insert(0, note.Note("C4", quarterLength=1))
    upper.insert(0, note.Note("G4", quarterLength=1))
    score.insert(0, lower)
    score.insert(0, upper)
    return score


def write_score(score: Any, path: Path) -> Path:
    output_format = "midi" if path.suffix.lower() in {".mid", ".midi"} else "musicxml"
    score.write(output_format, fp=str(path))
    return path
