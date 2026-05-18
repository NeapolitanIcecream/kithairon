"""Pitch inversion helpers."""

from __future__ import annotations

from kithairon.ir import Melody


def default_inversion_axis(melody: Melody) -> int:
    for event in melody.events:
        if event.pitch is not None:
            return event.pitch
    return 60


def invert_pitch(pitch: int | None, axis: int) -> int | None:
    if pitch is None:
        return None
    return (axis * 2) - pitch
