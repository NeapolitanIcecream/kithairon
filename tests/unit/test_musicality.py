from __future__ import annotations

from fractions import Fraction

from kithairon.ir import CanonCandidate, Melody, NoteEvent, TransformSpec, Voice
from kithairon.scoring.musicality import compute_musicality


def test_musicality_metrics_are_deterministic_and_separate_from_rule_score() -> None:
    candidate = _candidate(
        leader_pitches=(60, 62, 64, 65),
        follower_pitches=(48, 50, 52, 53),
        score=73.0,
    )

    first = compute_musicality(candidate)
    second = compute_musicality(candidate)

    assert first == second
    assert first.total != candidate.score
    assert set(first.raw_values) == {
        "repeated_note_density",
        "repeated_note_plateau_count",
        "melodic_leap_pressure",
        "contour_variety",
        "rhythmic_complementarity",
        "bass_independence_proxy",
    }


def test_repeated_static_candidate_gets_lower_musicality_than_varied_candidate() -> None:
    static = _candidate(
        leader_pitches=(60, 60, 60, 60),
        follower_pitches=(48, 48, 48, 48),
    )
    varied = _candidate(
        leader_pitches=(60, 62, 64, 65),
        follower_pitches=(48, 50, 52, 53),
    )

    static_breakdown = compute_musicality(static)
    varied_breakdown = compute_musicality(varied)

    assert static_breakdown.total < varied_breakdown.total
    assert static_breakdown.raw_values["repeated_note_density"] == 1.0
    assert static_breakdown.raw_values["repeated_note_plateau_count"] == 2.0


def test_musicality_can_be_computed_for_empty_candidate_without_crashing() -> None:
    candidate = _candidate(leader_pitches=(), follower_pitches=())

    breakdown = compute_musicality(candidate)

    assert 0 <= breakdown.total <= 100
    assert breakdown.raw_values["repeated_note_density"] == 0.0


def _candidate(
    *,
    leader_pitches: tuple[int, ...],
    follower_pitches: tuple[int, ...],
    score: float = 90.0,
) -> CanonCandidate:
    leader = Voice(
        name="leader",
        role="leader",
        melody=Melody(
            events=_events("l", leader_pitches),
            time_signature="4/4",
        ),
    )
    follower = Voice(
        name="follower",
        role="follower",
        melody=Melody(
            events=_events("f", follower_pitches),
            time_signature="4/4",
        ),
    )
    return CanonCandidate(
        id="candidate",
        voices=(leader, follower),
        transform_spec=TransformSpec(delay=Fraction(1)),
        engine="strict",
        strict_canon=True,
        score=score,
        violations=(),
    )


def _events(prefix: str, pitches: tuple[int, ...]) -> tuple[NoteEvent, ...]:
    return tuple(
        NoteEvent(
            id=f"{prefix}{index}",
            pitch=pitch,
            start=Fraction(index),
            duration=Fraction(1),
        )
        for index, pitch in enumerate(pitches)
    )
