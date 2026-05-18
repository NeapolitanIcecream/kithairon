"""Enumerate strict transform specs from generation configuration."""

from __future__ import annotations

from collections.abc import Iterable
from fractions import Fraction

from kithairon.config import GenerationConfig
from kithairon.ir import TransformMode, TransformSpec


def enumerate_transform_specs(config: GenerationConfig) -> Iterable[TransformSpec]:
    emitted = 0
    for delay in config.delays:
        for transform in config.transforms:
            for spec in _specs_for_transform(delay, transform, config.intervals):
                if emitted >= config.max_candidates:
                    return
                emitted += 1
                yield spec


def _specs_for_transform(
    delay: Fraction,
    transform: TransformMode,
    intervals: tuple[int, ...],
) -> Iterable[TransformSpec]:
    if transform == "identity":
        yield TransformSpec(delay=delay, transform_mode="identity")
        return

    if transform == "augmentation":
        yield TransformSpec(
            delay=delay,
            transform_mode="augmentation",
            rhythm_scale=Fraction(2),
        )
        return

    if transform == "diminution":
        yield TransformSpec(
            delay=delay,
            transform_mode="diminution",
            rhythm_scale=Fraction(1, 2),
        )
        return

    for interval in intervals:
        yield TransformSpec(delay=delay, interval=interval, transform_mode=transform)
