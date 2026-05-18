"""Apply strict canon transforms to melody IR."""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

from kithairon.ir import Melody, NoteEvent, TransformSpec
from kithairon.transforms.inversion import default_inversion_axis, invert_pitch
from kithairon.transforms.retrograde import retrograde_start
from kithairon.transforms.rhythm import effective_rhythm_scale, melody_duration
from kithairon.transforms.transpose import transpose_chromatic, transpose_diatonic


def apply_transform(melody: Melody, spec: TransformSpec) -> Melody:
    """Return a melody transformed by a deterministic strict-canon spec."""
    total_duration = melody_duration(melody)
    axis = (
        spec.inversion_axis if spec.inversion_axis is not None else default_inversion_axis(melody)
    )
    rhythm_scale = effective_rhythm_scale(spec.transform_mode, spec.rhythm_scale)

    events = tuple(
        sorted(
            (
                _transform_event(
                    event,
                    melody=melody,
                    spec=spec,
                    axis=axis,
                    rhythm_scale=rhythm_scale,
                    total_duration=total_duration,
                )
                for event in melody.events
            ),
            key=lambda event: (event.start, event.id),
        )
    )

    return replace(melody, events=events)


def _transform_event(
    event: NoteEvent,
    *,
    melody: Melody,
    spec: TransformSpec,
    axis: int,
    rhythm_scale: Fraction,
    total_duration: Fraction,
) -> NoteEvent:
    start = event.start
    duration = event.duration
    pitch = _mode_pitch(event.pitch, spec, axis, melody.key_hint)

    if spec.transform_mode == "retrograde":
        start = retrograde_start(event.start, event.duration, total_duration)

    start *= rhythm_scale
    duration *= rhythm_scale

    return replace(
        event,
        pitch=pitch,
        start=start + spec.delay,
        duration=duration,
    )


def _mode_pitch(
    pitch: int | None,
    spec: TransformSpec,
    axis: int,
    key_hint: str | None,
) -> int | None:
    transformed = invert_pitch(pitch, axis) if spec.transform_mode == "inversion" else pitch
    if spec.transpose_mode == "chromatic":
        return transpose_chromatic(transformed, spec.interval, spec.octave_displacement)
    return transpose_diatonic(transformed, spec.interval, key_hint)
