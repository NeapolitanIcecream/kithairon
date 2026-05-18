from __future__ import annotations

from fractions import Fraction

import pytest

from kithairon.config import GenerationConfig
from kithairon.errors import TransformError
from kithairon.ir import Melody, NoteEvent, TransformSpec
from kithairon.transforms.apply import apply_transform
from kithairon.transforms.enumerate import enumerate_transform_specs
from kithairon.transforms.spec import STRICT_TRANSFORM_MODES


def _melody() -> Melody:
    return Melody(
        events=(
            NoteEvent(id="n1", pitch=60, start=Fraction(0), duration=Fraction(1)),
            NoteEvent(id="n2", pitch=62, start=Fraction(1), duration=Fraction(1, 2)),
            NoteEvent(id="n3", pitch=None, start=Fraction(3, 2), duration=Fraction(1, 2)),
            NoteEvent(id="n4", pitch=64, start=Fraction(2), duration=Fraction(1)),
        ),
        time_signature="4/4",
        tempo_bpm=120,
        key_hint="C major",
        source_path="theme.musicxml",
    )


def test_strict_transform_modes_match_step_four_scope() -> None:
    assert STRICT_TRANSFORM_MODES == (
        "identity",
        "transposition",
        "inversion",
        "retrograde",
        "augmentation",
        "diminution",
    )


def test_delay_transform_only_changes_event_starts() -> None:
    transformed = apply_transform(_melody(), TransformSpec(delay=Fraction(2)))

    assert [event.start for event in transformed.events] == [
        Fraction(2),
        Fraction(3),
        Fraction(7, 2),
        Fraction(4),
    ]
    assert [event.duration for event in transformed.events] == [
        Fraction(1),
        Fraction(1, 2),
        Fraction(1, 2),
        Fraction(1),
    ]
    assert [event.pitch for event in transformed.events] == [60, 62, None, 64]


def test_chromatic_transposition_changes_pitches_only() -> None:
    transformed = apply_transform(
        _melody(),
        TransformSpec(delay=Fraction(0), interval=7, transform_mode="transposition"),
    )

    assert [event.pitch for event in transformed.events] == [67, 69, None, 71]
    assert [event.start for event in transformed.events] == [
        Fraction(0),
        Fraction(1),
        Fraction(3, 2),
        Fraction(2),
    ]
    assert [event.duration for event in transformed.events] == [
        Fraction(1),
        Fraction(1, 2),
        Fraction(1, 2),
        Fraction(1),
    ]


def test_inversion_mirrors_pitches_around_axis() -> None:
    transformed = apply_transform(
        _melody(),
        TransformSpec(delay=Fraction(0), transform_mode="inversion", inversion_axis=62),
    )

    assert [event.pitch for event in transformed.events] == [64, 62, None, 60]


def test_retrograde_reverses_starts_within_total_duration() -> None:
    transformed = apply_transform(
        _melody(),
        TransformSpec(delay=Fraction(0), transform_mode="retrograde"),
    )

    assert [(event.id, event.start, event.duration) for event in transformed.events] == [
        ("n4", Fraction(0), Fraction(1)),
        ("n3", Fraction(1), Fraction(1, 2)),
        ("n2", Fraction(3, 2), Fraction(1, 2)),
        ("n1", Fraction(2), Fraction(1)),
    ]


def test_augmentation_and_diminution_scale_rhythm() -> None:
    augmented = apply_transform(
        _melody(),
        TransformSpec(
            delay=Fraction(0),
            transform_mode="augmentation",
            rhythm_scale=Fraction(2),
        ),
    )
    diminished = apply_transform(
        _melody(),
        TransformSpec(
            delay=Fraction(0),
            transform_mode="diminution",
            rhythm_scale=Fraction(1, 2),
        ),
    )

    assert [event.start for event in augmented.events] == [0, 2, 3, 4]
    assert [event.duration for event in augmented.events] == [2, 1, 1, 2]
    assert [event.start for event in diminished.events] == [
        Fraction(0),
        Fraction(1, 2),
        Fraction(3, 4),
        Fraction(1),
    ]
    assert [event.duration for event in diminished.events] == [
        Fraction(1, 2),
        Fraction(1, 4),
        Fraction(1, 4),
        Fraction(1, 2),
    ]


def test_diatonic_transposition_interface_is_reserved() -> None:
    with pytest.raises(TransformError) as raised:
        apply_transform(
            _melody(),
            TransformSpec(
                delay=Fraction(0),
                interval=2,
                transpose_mode="diatonic",
                transform_mode="transposition",
            ),
        )

    assert raised.value.to_diagnostic()["code"] == "diatonic_transposition_not_implemented"


def test_enumerate_transform_specs_uses_generation_config_order_and_limit() -> None:
    config = GenerationConfig(
        delays=(Fraction(1), Fraction(2)),
        intervals=(0, 7),
        transforms=("identity", "transposition", "augmentation", "diminution"),
        max_candidates=6,
    )

    specs = tuple(enumerate_transform_specs(config))

    assert len(specs) == 6
    assert specs[0] == TransformSpec(delay=Fraction(1), transform_mode="identity")
    assert (
        TransformSpec(
            delay=Fraction(1),
            interval=7,
            transform_mode="transposition",
        )
        in specs
    )
    assert (
        TransformSpec(
            delay=Fraction(1),
            transform_mode="augmentation",
            rhythm_scale=Fraction(2),
        )
        in specs
    )
