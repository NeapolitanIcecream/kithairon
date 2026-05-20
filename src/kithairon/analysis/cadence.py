"""Cadence summary analysis for composition assistance."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Literal

from kithairon.analysis.context import AnalysisContext
from kithairon.analysis.phrasing import PhraseSpan
from kithairon.analysis.verticality import Verticality

type CadenceStrength = Literal["strong", "moderate", "weak"]
type CadenceType = Literal[
    "open_phrase",
    "half_cadence_tendency",
    "authentic_close_tendency",
    "weak_close",
    "ambiguous_close",
]

_CONSONANT_FINAL_INTERVALS = {"P1", "P5", "P8", "m3", "M3", "m6", "M6"}
_CADENTIAL_MOTIONS = {1, 2, 5, 7, 12}


@dataclass(frozen=True)
class CadenceSummary:
    cadence_id: str
    bar: int
    beat: Fraction
    strength: CadenceStrength
    cadence_type: CadenceType
    final_interval: str
    bass_motion: int | None
    upper_motion: int | None
    event_ids: tuple[str, ...]
    label: str
    rationale: str


def summarize_cadence(context: AnalysisContext) -> CadenceSummary | None:
    """Summarize the final cadence implied by the last two verticalities."""
    cadences = summarize_cadences(context)
    return cadences[-1] if cadences else None


def summarize_cadences(
    context: AnalysisContext,
    phrases: tuple[PhraseSpan, ...] = (),
) -> tuple[CadenceSummary, ...]:
    """Classify final and phrase-ending cadence points."""
    if not context.verticalities:
        return ()
    if not phrases:
        final = context.verticalities[-1]
        previous = _previous_verticality(context.verticalities, final)
        return (_cadence_summary("final-cadence", final, previous, is_final=True),)

    cadences: list[CadenceSummary] = []
    for phrase in phrases:
        final = _last_verticality_at_or_before_bar(context.verticalities, phrase.bar_end)
        if final is None:
            continue
        previous = _previous_verticality(context.verticalities, final)
        is_final = final == context.verticalities[-1] or phrase == phrases[-1]
        cadence_id = "final-cadence" if is_final else f"{phrase.phrase_id}-cadence"
        cadences.append(_cadence_summary(cadence_id, final, previous, is_final=is_final))
    return tuple(cadences)


def _cadence_summary(
    cadence_id: str,
    final: Verticality,
    previous: Verticality | None,
    *,
    is_final: bool,
) -> CadenceSummary:
    bass_motion = _voice_motion(previous, final, final.lower_voice)
    upper_motion = _voice_motion(previous, final, final.upper_voice)
    strength = _cadence_strength(final, bass_motion)
    cadence_type = _cadence_type(final, bass_motion, strength, is_final=is_final)
    event_ids = tuple(
        f"{voice_name}:{event_id}" for voice_name, event_id in sorted(final.event_ids.items())
    )
    return CadenceSummary(
        cadence_id=cadence_id,
        bar=final.bar,
        beat=final.beat,
        strength=strength,
        cadence_type=cadence_type,
        final_interval=final.interval_name,
        bass_motion=bass_motion,
        upper_motion=upper_motion,
        event_ids=event_ids,
        label=_label(cadence_type),
        rationale=_rationale(final, bass_motion, strength, cadence_type),
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


def _cadence_type(
    final: Verticality,
    bass_motion: int | None,
    strength: CadenceStrength,
    *,
    is_final: bool,
) -> CadenceType:
    if not is_final:
        if final.simple_interval_name == "P5":
            return "half_cadence_tendency"
        return "open_phrase"
    if strength == "strong" and final.simple_interval_name in {"P1", "P8"}:
        return "authentic_close_tendency"
    if final.simple_interval_name == "P5" and bass_motion not in {None, 0}:
        return "half_cadence_tendency"
    if strength == "weak":
        return "weak_close"
    return "ambiguous_close"


def _label(cadence_type: CadenceType) -> str:
    return cadence_type.replace("_", " ").title()


def _previous_verticality(
    verticalities: tuple[Verticality, ...],
    final: Verticality,
) -> Verticality | None:
    index = verticalities.index(final)
    return verticalities[index - 1] if index > 0 else None


def _last_verticality_at_or_before_bar(
    verticalities: tuple[Verticality, ...],
    bar: int,
) -> Verticality | None:
    eligible = [verticality for verticality in verticalities if verticality.bar <= bar]
    return eligible[-1] if eligible else None


def _rationale(
    final: Verticality,
    bass_motion: int | None,
    strength: CadenceStrength,
    cadence_type: CadenceType,
) -> str:
    bass = "unknown" if bass_motion is None else f"{bass_motion:+d}"
    return (
        f"{_label(cadence_type)} ({strength}): final interval {final.simple_interval_name}, "
        f"bass motion {bass}."
    )
