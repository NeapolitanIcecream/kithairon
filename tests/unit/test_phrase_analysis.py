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


def test_build_phrase_spans_reports_arrival_high_point_and_warnings() -> None:
    candidate = _candidate(
        leader_pitches=(60, 60, 60, 61),
        follower_pitches=(48, 48, 48, 48),
        starts=(Fraction(0), Fraction(1), Fraction(2), Fraction(3)),
    )

    phrase = build_phrase_spans(candidate, bars_per_phrase=1)[0]

    assert phrase.high_point_event_id == "leader:l3"
    assert phrase.high_point_pitch == 61
    assert phrase.arrival_event_id == "leader:l3"
    assert phrase.arrival_pitch == 61
    assert phrase.repeated_note_plateaus == (
        "leader:l0",
        "leader:l1",
        "leader:l2",
        "follower:f0",
        "follower:f1",
        "follower:f2",
        "follower:f3",
    )
    assert phrase.flat_sequence_warning is True
    assert set(phrase.warnings) == {"repeated_note_plateau", "flat_sequence"}


def _candidate(
    *,
    leader_pitches: tuple[int, ...],
    follower_pitches: tuple[int, ...],
    starts: tuple[Fraction, ...] | None = None,
) -> CanonCandidate:
    return CanonCandidate(
        id="analysis_case",
        voices=(
            Voice(
                name="leader",
                role="leader",
                melody=_melody("l", leader_pitches, starts),
            ),
            Voice(
                name="follower",
                role="follower",
                melody=_melody("f", follower_pitches, starts),
            ),
        ),
        transform_spec=TransformSpec(delay=Fraction(0)),
        engine="strict",
        strict_canon=True,
        score=0,
        violations=(),
    )


def _melody(
    prefix: str,
    pitches: tuple[int, ...],
    starts: tuple[Fraction, ...] | None,
) -> Melody:
    event_starts = starts or tuple(Fraction(index * 4) for index in range(len(pitches)))
    return Melody(
        events=tuple(
            NoteEvent(
                id=f"{prefix}{index}",
                pitch=pitch,
                start=event_starts[index],
                duration=Fraction(1),
            )
            for index, pitch in enumerate(pitches)
        ),
        time_signature="4/4",
    )
