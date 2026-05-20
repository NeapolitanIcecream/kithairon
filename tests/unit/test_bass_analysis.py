from __future__ import annotations

from fractions import Fraction

from kithairon.analysis import summarize_bass_support
from kithairon.ir import CanonCandidate, Melody, NoteEvent, TransformSpec, Voice


def test_summarize_bass_support_flags_static_repeated_bass() -> None:
    summary = summarize_bass_support(_candidate(follower_pitches=(48, 48, 48, 48)))

    assert summary is not None
    assert summary.voice_id == "follower"
    assert summary.static_bass is True
    assert summary.motion_label == "static"
    assert summary.repeated_note_ratio == 1.0
    assert summary.unique_pitch_count == 1
    assert summary.strong_beat_support_event_ids == ("follower:f0",)
    assert summary.root_support_proxy == 1.0
    assert summary.sustained_foundation_score == 1.0
    assert summary.bass_independence_score == 0.275


def test_summarize_bass_support_labels_stepwise_motion() -> None:
    summary = summarize_bass_support(_candidate(follower_pitches=(48, 50, 52, 53)))

    assert summary is not None
    assert summary.static_bass is False
    assert summary.motion_label == "stepwise"
    assert summary.stepwise_motion_ratio == 1.0
    assert summary.strong_beat_support_event_ids == ("follower:f0",)
    assert summary.root_support_proxy == 1.0
    assert summary.bass_independence_score > 0.8


def _candidate(*, follower_pitches: tuple[int, ...]) -> CanonCandidate:
    return CanonCandidate(
        id="bass_case",
        voices=(
            Voice(
                name="leader",
                role="leader",
                melody=_melody("l", (60, 62, 64, 65)),
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
                start=Fraction(index),
                duration=Fraction(1),
            )
            for index, pitch in enumerate(pitches)
        ),
        time_signature="4/4",
    )
