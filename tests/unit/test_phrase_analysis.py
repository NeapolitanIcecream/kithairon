from __future__ import annotations

from fractions import Fraction

from kithairon.analysis import build_phrase_spans
from kithairon.ir import CanonCandidate, Melody, NoteEvent, TransformSpec, Voice


def test_build_phrase_spans_groups_candidate_into_two_bar_units() -> None:
    candidate = _candidate(
        leader_pitches=(60, 62, 64, 65),
        follower_pitches=(48, 50, 52, 53),
    )

    phrases = build_phrase_spans(candidate)

    assert [(phrase.bar_start, phrase.bar_end) for phrase in phrases] == [(1, 2), (3, 4)]
    assert [phrase.note_count for phrase in phrases] == [4, 4]
    assert phrases[0].event_ids == ("leader:l0", "leader:l1", "follower:f0", "follower:f1")


def _candidate(
    *,
    leader_pitches: tuple[int, ...],
    follower_pitches: tuple[int, ...],
) -> CanonCandidate:
    return CanonCandidate(
        id="analysis_case",
        voices=(
            Voice(
                name="leader",
                role="leader",
                melody=_melody("l", leader_pitches),
            ),
            Voice(
                name="follower",
                role="follower",
                melody=_melody("f", follower_pitches),
            ),
        ),
        transform_spec=TransformSpec(delay=Fraction(0)),
        engine="strict",
        strict_canon=True,
        score=0,
        violations=(),
    )


def _melody(prefix: str, pitches: tuple[int, ...]) -> Melody:
    return Melody(
        events=tuple(
            NoteEvent(
                id=f"{prefix}{index}",
                pitch=pitch,
                start=Fraction(index * 4),
                duration=Fraction(1),
            )
            for index, pitch in enumerate(pitches)
        ),
        time_signature="4/4",
    )
