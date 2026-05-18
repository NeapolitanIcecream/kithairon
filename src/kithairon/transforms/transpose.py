"""Pitch transposition helpers."""

from __future__ import annotations

from kithairon.errors import TransformError


def transpose_chromatic(
    pitch: int | None, interval: int, octave_displacement: int = 0
) -> int | None:
    if pitch is None:
        return None
    return pitch + interval + (octave_displacement * 12)


def transpose_diatonic(pitch: int | None, interval: int, key_hint: str | None = None) -> int | None:
    raise TransformError(
        "Diatonic transposition is reserved for a later implementation step.",
        code="diatonic_transposition_not_implemented",
        details={"pitch": pitch, "interval": interval, "key_hint": key_hint or ""},
    )
