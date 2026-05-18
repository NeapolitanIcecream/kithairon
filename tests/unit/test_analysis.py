from __future__ import annotations

from fractions import Fraction

from kithairon.analysis import analyze_candidate, build_time_slices
from kithairon.ir import CanonCandidate, Melody, NoteEvent, TransformSpec, Voice


def _melody(events: tuple[NoteEvent, ...], time_signature: str = "4/4") -> Melody:
    return Melody(events=events, time_signature=time_signature, tempo_bpm=96, key_hint="C major")


def _candidate(time_signature: str = "4/4") -> CanonCandidate:
    leader = _melody(
        (
            NoteEvent(id="l1", pitch=60, start=Fraction(0), duration=Fraction(1)),
            NoteEvent(id="l2", pitch=62, start=Fraction(1), duration=Fraction(1)),
            NoteEvent(id="l3", pitch=64, start=Fraction(2), duration=Fraction(1)),
        ),
        time_signature,
    )
    follower = _melody(
        (
            NoteEvent(id="f1", pitch=48, start=Fraction(0), duration=Fraction(1)),
            NoteEvent(id="f2", pitch=50, start=Fraction(1), duration=Fraction(1)),
            NoteEvent(id="f3", pitch=52, start=Fraction(2), duration=Fraction(1)),
        ),
        time_signature,
    )
    return CanonCandidate(
        id="analysis_case",
        voices=(
            Voice(name="leader", melody=leader, role="leader"),
            Voice(name="follower", melody=follower, role="follower"),
        ),
        transform_spec=TransformSpec(delay=Fraction(0)),
        engine="strict",
        strict_canon=True,
        score=0.0,
        violations=(),
    )


def test_build_time_slices_tracks_active_events_across_beat_boundaries() -> None:
    sustained = _melody(
        (NoteEvent(id="upper", pitch=60, start=Fraction(0), duration=Fraction(4)),)
    )
    pulse = _melody(
        (
            NoteEvent(id="lower1", pitch=48, start=Fraction(0), duration=Fraction(1)),
            NoteEvent(id="lower2", pitch=50, start=Fraction(1), duration=Fraction(1)),
            NoteEvent(id="lower3", pitch=52, start=Fraction(2), duration=Fraction(1)),
            NoteEvent(id="lower4", pitch=53, start=Fraction(3), duration=Fraction(1)),
        )
    )

    slices = build_time_slices(
        (
            Voice(name="upper", melody=sustained, role="leader"),
            Voice(name="lower", melody=pulse, role="follower"),
        ),
        time_signature="4/4",
    )

    assert [time_slice.start for time_slice in slices] == [0, 1, 2, 3]
    assert [time_slice.active_events["upper"].id for time_slice in slices] == [
        "upper",
        "upper",
        "upper",
        "upper",
    ]
    assert [time_slice.beat for time_slice in slices] == [1, 2, 3, 4]
    assert [time_slice.beat_strength for time_slice in slices] == [
        "strong",
        "weak",
        "medium",
        "weak",
    ]


def test_build_time_slices_recognizes_three_four_downbeats_and_weak_beats() -> None:
    melody = _melody(
        (
            NoteEvent(id="n1", pitch=60, start=Fraction(0), duration=Fraction(1)),
            NoteEvent(id="n2", pitch=62, start=Fraction(1), duration=Fraction(1)),
            NoteEvent(id="n3", pitch=64, start=Fraction(2), duration=Fraction(1)),
            NoteEvent(id="n4", pitch=65, start=Fraction(3), duration=Fraction(1)),
        ),
        "3/4",
    )

    slices = build_time_slices(
        (Voice(name="leader", melody=melody, role="leader"),),
        time_signature="3/4",
    )

    metric_positions = [
        (time_slice.bar, time_slice.beat, time_slice.beat_strength) for time_slice in slices
    ]

    assert metric_positions == [
        (1, Fraction(1), "strong"),
        (1, Fraction(2), "weak"),
        (1, Fraction(3), "weak"),
        (2, Fraction(1), "strong"),
    ]


def test_analyze_candidate_identifies_vertical_intervals() -> None:
    context = analyze_candidate(_candidate())

    assert [verticality.semitones for verticality in context.verticalities] == [12, 12, 12]
    assert [verticality.interval_name for verticality in context.verticalities] == [
        "P8",
        "P8",
        "P8",
    ]
    assert context.verticalities[0].lower_voice == "follower"
    assert context.verticalities[0].upper_voice == "leader"


def test_analyze_candidate_generates_voice_leading_quartets() -> None:
    context = analyze_candidate(_candidate())

    assert len(context.voice_leadings) == 2
    assert all(voice_leading.parallel_octave for voice_leading in context.voice_leadings)
    assert [voice_leading.motion_type for voice_leading in context.voice_leadings] == [
        "parallel",
        "parallel",
    ]
