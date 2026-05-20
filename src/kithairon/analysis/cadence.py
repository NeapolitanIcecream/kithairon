"""Cadence summary analysis for composition assistance."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Literal

from kithairon.analysis.context import AnalysisContext
from kithairon.analysis.verticality import Verticality

type CadenceStrength = Literal["strong", "moderate", "weak"]

_CONSONANT_FINAL_INTERVALS = {"P1", "P5", "P8", "m3", "M3", "m6", "M6"}
_CADENTIAL_MOTIONS = {1, 2, 5, 7, 12}


@dataclass(frozen=True)
class CadenceSummary:
    cadence_id: str
    bar: int
    beat: Fraction
    strength: CadenceStrength
    final_interval: str
    bass_motion: int | None
    upper_motion: int | None
    event_ids: tuple[str, ...]
    label: str
    rationale: str


def summarize_cadence(context: AnalysisContext) -> CadenceSummary | None:
    """Summarize the final cadence implied by the last two verticalities."""
    if not context.verticalities:
        return None

    final = context.verticalities[-1]
    previous = context.verticalities[-2] if len(context.verticalities) >= 2 else None
    bass_motion = _voice_motion(previous, final, final.lower_voice)
    upper_motion = _voice_motion(previous, final, final.upper_voice)
    strength = _cadence_strength(final, bass_motion)
    event_ids = tuple(
        f"{voice_name}:{event_id}"
        for voice_name, event_id in sorted(final.event_ids.items())
    )
    return CadenceSummary(
        cadence_id="final-cadence",
        bar=final.bar,
        beat=final.beat,
        strength=strength,
        final_interval=final.interval_name,
        bass_motion=bass_motion,
        upper_motion=upper_motion,
        event_ids=event_ids,
        label=f"{strength.title()} final cadence",
        rationale=_rationale(final, bass_motion, strength),
    )


def _voice_motion(
    previous: Verticality | None,
    final: Verticality,
    voice_name: str,
) -> int | None:
    if previous is None or voice_name not in previous.pitches or voice_name not in final.pitches:
        return None
    return final.pitches[voice_name] - previous.pitches[voice_name]


def _cadence_strength(final: Verticality, bass_motion: int | None) -> CadenceStrength:
    if final.simple_interval_name not in _CONSONANT_FINAL_INTERVALS:
        return "weak"
    if bass_motion is None or bass_motion == 0:
        return "weak"
    if final.beat_strength == "strong" and abs(bass_motion) in _CADENTIAL_MOTIONS:
        return "strong"
    return "moderate"


def _rationale(final: Verticality, bass_motion: int | None, strength: CadenceStrength) -> str:
    bass = "unknown" if bass_motion is None else f"{bass_motion:+d}"
    return (
        f"{strength.title()} cadence: final interval {final.simple_interval_name}, "
        f"bass motion {bass}."
    )
