"""Rhythmic transform helpers."""

from __future__ import annotations

from fractions import Fraction

from kithairon.ir import Melody, TransformMode


def melody_duration(melody: Melody) -> Fraction:
    return max((event.start + event.duration for event in melody.events), default=Fraction(0))


def effective_rhythm_scale(transform_mode: TransformMode, rhythm_scale: Fraction) -> Fraction:
    if rhythm_scale != 1:
        return rhythm_scale
    if transform_mode == "augmentation":
        return Fraction(2)
    if transform_mode == "diminution":
        return Fraction(1, 2)
    return Fraction(1)
