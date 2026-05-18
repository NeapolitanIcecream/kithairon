# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false

from __future__ import annotations

from fractions import Fraction
from typing import cast

from hypothesis import given
from hypothesis import strategies as st

from kithairon.ir import CanonCandidate, Melody, NoteEvent, TransformMode, TransformSpec, Voice
from kithairon.transforms.apply import apply_transform


@st.composite
def monophonic_melodies(draw: st.DrawFn) -> Melody:
    pitches = draw(st.lists(st.integers(min_value=48, max_value=84), min_size=1, max_size=8))
    durations = draw(
        st.lists(
            st.sampled_from([Fraction(1, 4), Fraction(1, 2), Fraction(1), Fraction(2)]),
            min_size=len(pitches),
            max_size=len(pitches),
        )
    )
    events: list[NoteEvent] = []
    start = Fraction(0)
    for index, pitch in enumerate(pitches):
        duration = durations[index]
        events.append(
            NoteEvent(
                id=f"n{index:04d}",
                pitch=pitch,
                start=start,
                duration=duration,
            )
        )
        start += duration
    return Melody(events=tuple(events), time_signature="4/4")


@st.composite
def transform_specs(draw: st.DrawFn) -> TransformSpec:
    mode = draw(
        st.sampled_from(
            [
                "identity",
                "transposition",
                "inversion",
                "retrograde",
                "augmentation",
                "diminution",
            ]
        )
    )
    return TransformSpec(
        delay=Fraction(draw(st.integers(min_value=0, max_value=8))),
        interval=draw(st.integers(min_value=-12, max_value=12)),
        transform_mode=cast(TransformMode, mode),
        inversion_axis=draw(st.one_of(st.none(), st.integers(min_value=48, max_value=84))),
        rhythm_scale=draw(st.sampled_from([Fraction(1, 2), Fraction(1), Fraction(2)])),
    )


@given(monophonic_melodies(), st.integers(min_value=-12, max_value=12))
def test_transposition_preserves_rhythm(melody: Melody, interval: int) -> None:
    transformed = apply_transform(
        melody,
        TransformSpec(
            delay=Fraction(0),
            interval=interval,
            transform_mode="transposition",
        ),
    )

    assert [(event.start, event.duration) for event in transformed.events] == [
        (event.start, event.duration) for event in melody.events
    ]


@given(monophonic_melodies(), st.integers(min_value=0, max_value=8))
def test_delay_preserves_pitch_and_duration(melody: Melody, delay: int) -> None:
    transformed = apply_transform(melody, TransformSpec(delay=Fraction(delay)))

    assert [event.pitch for event in transformed.events] == [event.pitch for event in melody.events]
    assert [event.duration for event in transformed.events] == [
        event.duration for event in melody.events
    ]
    assert [event.start for event in transformed.events] == [
        event.start + delay for event in melody.events
    ]


@given(monophonic_melodies(), st.integers(min_value=48, max_value=84))
def test_inversion_twice_around_same_axis_returns_original_pitches(
    melody: Melody,
    axis: int,
) -> None:
    inverted = apply_transform(
        melody,
        TransformSpec(delay=Fraction(0), transform_mode="inversion", inversion_axis=axis),
    )
    restored = apply_transform(
        inverted,
        TransformSpec(delay=Fraction(0), transform_mode="inversion", inversion_axis=axis),
    )

    assert [event.pitch for event in restored.events] == [event.pitch for event in melody.events]


@given(monophonic_melodies())
def test_retrograde_twice_preserves_total_duration_and_note_durations(melody: Melody) -> None:
    retrograde = apply_transform(
        melody, TransformSpec(delay=Fraction(0), transform_mode="retrograde")
    )
    restored = apply_transform(
        retrograde,
        TransformSpec(delay=Fraction(0), transform_mode="retrograde"),
    )

    assert melody_total_duration(restored) == melody_total_duration(melody)
    assert [(event.start, event.duration) for event in restored.events] == [
        (event.start, event.duration) for event in melody.events
    ]


@given(monophonic_melodies())
def test_augmentation_then_diminution_returns_original_rhythm(melody: Melody) -> None:
    augmented = apply_transform(
        melody,
        TransformSpec(
            delay=Fraction(0),
            transform_mode="augmentation",
            rhythm_scale=Fraction(2),
        ),
    )
    restored = apply_transform(
        augmented,
        TransformSpec(
            delay=Fraction(0),
            transform_mode="diminution",
            rhythm_scale=Fraction(1, 2),
        ),
    )

    assert [(event.start, event.duration) for event in restored.events] == [
        (event.start, event.duration) for event in melody.events
    ]


@given(monophonic_melodies(), st.integers(min_value=-12, max_value=12))
def test_strict_candidate_follower_equals_apply_transform(melody: Melody, interval: int) -> None:
    spec = TransformSpec(delay=Fraction(2), interval=interval, transform_mode="transposition")
    follower = apply_transform(melody, spec)

    candidate = CanonCandidate(
        id="strict_property",
        voices=(
            Voice(name="leader", melody=melody, role="leader"),
            Voice(name="follower", melody=follower, role="follower"),
        ),
        transform_spec=spec,
        engine="strict",
        strict_canon=True,
        score=100.0,
        violations=(),
    )

    assert candidate.voices[1].melody == apply_transform(candidate.voices[0].melody, spec)


@given(monophonic_melodies(), transform_specs())
def test_transform_preserves_monophonic_non_overlapping_timeline(
    melody: Melody,
    spec: TransformSpec,
) -> None:
    transformed = apply_transform(melody, spec)

    previous_end = Fraction(0)
    for event in transformed.events:
        assert event.duration > 0
        assert event.start >= previous_end
        previous_end = event.start + event.duration


def melody_total_duration(melody: Melody) -> Fraction:
    return max((event.start + event.duration for event in melody.events), default=Fraction(0))
