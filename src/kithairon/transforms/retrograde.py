"""Retrograde time helpers."""

from __future__ import annotations

from fractions import Fraction


def retrograde_start(start: Fraction, duration: Fraction, total_duration: Fraction) -> Fraction:
    return total_duration - (start + duration)
