from __future__ import annotations

from fractions import Fraction

from kithairon.analysis import (
    analyze_candidate,
    build_phrase_spans,
    summarize_cadence,
    summarize_cadences,
)
from kithairon.ir import CanonCandidate, Melody, NoteEvent, TransformSpec, Voice


def test_summarize_cadence_marks_static_final_bass_motion_as_weak() -> None:
    context = analyze_candidate(
        _candidate(
            leader_pitches=(60, 62, 60),
            follower_pitches=(48, 48, 48),
        )
    )

    cadence = summarize_cadence(context)

    assert cadence is not None
    assert cadence.strength == "weak"
    assert cadence.final_interval == "P8"
    assert cadence.cadence_type == "weak_close"
    assert cadence.bass_motion == 0
    assert cadence.event_ids == ("follower:f2", "leader:l2")


def test_summarize_cadence_marks_consonant_downbeat_resolution_as_strong() -> None:
    context = analyze_candidate(
        _candidate(
            leader_pitches=(62, 60),
            follower_pitches=(43, 48),
            starts=(Fraction(3), Fraction(4)),
        )
    )

    cadence = summarize_cadence(context)

    assert cadence is not None
    assert cadence.strength == "strong"
    assert cadence.cadence_type == "authentic_close_tendency"
    assert cadence.bar == 2
    assert cadence.bass_motion == 5


def test_summarize_cadences_classifies_internal_and_final_phrase_endings() -> None:
    candidate = _candidate(
        leader_pitches=(52, 60),
        follower_pitches=(43, 48),
        starts=(Fraction(0), Fraction(4)),
    )
    context = analyze_candidate(candidate)
    phrases = build_phrase_spans(candidate, bars_per_phrase=1)

    cadences = summarize_cadences(context, phrases)

    assert [(cadence.bar, cadence.cadence_type) for cadence in cadences] == [
        (1, "open_phrase"),
        (2, "authentic_close_tendency"),
    ]


def _candidate(
    *,
    leader_pitches: tuple[int, ...],
    follower_pitches: tuple[int, ...],
    starts: tuple[Fraction, ...] | None = None,
) -> CanonCandidate:
    return CanonCandidate(
        id="cadence_case",
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
    event_starts = starts or tuple(Fraction(index) for index in range(len(pitches)))
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
