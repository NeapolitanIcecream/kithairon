"""Transform mode constants."""

from __future__ import annotations

from kithairon.ir import TransformMode

STRICT_TRANSFORM_MODES: tuple[TransformMode, ...] = (
    "identity",
    "transposition",
    "inversion",
    "retrograde",
    "augmentation",
    "diminution",
)
