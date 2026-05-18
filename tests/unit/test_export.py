# pyright: reportUnknownMemberType=false

from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from typing import Any, cast

from music21 import converter

from kithairon.export import candidate_to_score, write_candidate_exports
from kithairon.ir import CanonCandidate, Melody, NoteEvent, TransformSpec, Voice


def _candidate() -> CanonCandidate:
    leader = Melody(
        events=(NoteEvent(id="l1", pitch=60, start=Fraction(0), duration=Fraction(1)),),
        time_signature="4/4",
        tempo_bpm=100,
    )
    follower = Melody(
        events=(NoteEvent(id="f1", pitch=72, start=Fraction(1), duration=Fraction(1)),),
        time_signature="4/4",
        tempo_bpm=100,
    )
    return CanonCandidate(
        id="export_case",
        voices=(
            Voice(name="leader", melody=leader, role="leader"),
            Voice(name="follower", melody=follower, role="follower"),
        ),
        transform_spec=TransformSpec(
            delay=Fraction(1),
            interval=12,
            transform_mode="transposition",
        ),
        engine="strict",
        strict_canon=True,
        score=92.0,
        violations=(),
    )


def test_candidate_to_score_builds_two_part_music21_score() -> None:
    score = candidate_to_score(_candidate())

    assert len(score.parts) == 2
    assert [part.partName for part in score.parts] == ["leader", "follower"]


def test_write_candidate_exports_writes_musicxml_and_midi(tmp_path: Path) -> None:
    paths = write_candidate_exports(_candidate(), tmp_path, stem="candidate")

    assert paths.musicxml.exists()
    assert paths.midi.exists()
    assert paths.musicxml.stat().st_size > 0
    assert paths.midi.stat().st_size > 0
    parsed_score = cast(Any, converter.parse(paths.musicxml))
    assert len(parsed_score.parts) == 2
