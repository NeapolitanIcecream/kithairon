"""Small deterministic objective layer for first-pass phrase polish ranking."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from itertools import pairwise

from kithairon.analysis.composition import CompositionAnalysis, analyze_composition
from kithairon.analysis.timeline import TimeSignatureInfo, parse_time_signature
from kithairon.ir import CanonCandidate, NoteEvent, VoiceRole
from kithairon.polish.models import ObjectivePreset, PolishObjectiveWeights, PolishRequest


@dataclass(frozen=True)
class ObjectiveEvaluation:
    total: float
    components: Mapping[str, float]
    weights: Mapping[str, float]


_PRESET_WEIGHTS: Mapping[ObjectivePreset, Mapping[str, float]] = {
    "reduce_repetition": {
        "repeated_note_penalty": 2.5,
        "leap_penalty": 0.7,
        "bass_smoothness_penalty": 0.6,
        "cadence_motion_reward": 0.2,
    },
    "smooth_bass": {
        "repeated_note_penalty": 0.7,
        "leap_penalty": 1.2,
        "bass_smoothness_penalty": 2.2,
        "cadence_motion_reward": 0.2,
    },
    "strengthen_cadence": {
        "repeated_note_penalty": 0.8,
        "leap_penalty": 0.8,
        "bass_smoothness_penalty": 0.8,
        "cadence_motion_reward": 2.2,
    },
    "general_polish": {
        "repeated_note_penalty": 1.0,
        "leap_penalty": 1.0,
        "bass_smoothness_penalty": 1.0,
        "cadence_motion_reward": 0.8,
    },
}


def evaluate_objective(
    candidate: CanonCandidate,
    request: PolishRequest,
    *,
    rewrite_role: VoiceRole,
    parent: CanonCandidate | None = None,
) -> ObjectiveEvaluation:
    """Return a bounded musical-shape adjustment for ranking local variants."""
    weights = effective_weights(request.objective_preset, request.objective_overrides)
    events = _selected_pitched_events(candidate, request, rewrite_role)
    components = {
        "repeated_note_penalty": -3.0 * _repeated_note_count(events),
        "leap_penalty": -0.35 * _excess_leap_pressure(events),
        "bass_smoothness_penalty": -0.3 * _bass_leap_pressure(events, rewrite_role),
        "cadence_motion_reward": 1.8 * _cadence_motion_value(events),
    }
    if request.search_mode == "rewrite_selected_voice" and parent is not None:
        if rewrite_role == "follower":
            components.update(_lower_invention_components(parent, candidate, request))
            weights = {
                **weights,
                "bass_root_support_reward": 5.0,
                "bass_foundation_reward": 2.0,
                "bass_independence_reward": 3.0,
                "static_bass_penalty": 1.6,
                "cadence_support_reward": 1.4,
            }
        elif rewrite_role == "leader":
            components.update(_upper_invention_components(parent, candidate, request, events))
            weights = {
                **weights,
                "phrase_warning_reduction_reward": 5.0,
                "plateau_reduction_reward": 3.0,
                "contour_variety_reward": 1.6,
                "cadence_clarity_reward": 1.6,
            }
    total = sum(components[name] * weights[name] for name in components)
    return ObjectiveEvaluation(
        total=round(total, 4),
        components={name: round(value, 4) for name, value in components.items()},
        weights=weights,
    )


def effective_weights(
    preset: ObjectivePreset,
    overrides: PolishObjectiveWeights,
) -> Mapping[str, float]:
    weights = dict(_PRESET_WEIGHTS[preset])
    for key, value in overrides.model_dump(exclude_none=True).items():
        weights[key] = float(value)
    return weights


def _selected_pitched_events(
    candidate: CanonCandidate,
    request: PolishRequest,
    rewrite_role: VoiceRole,
) -> tuple[NoteEvent, ...]:
    voice = next(voice for voice in candidate.voices if voice.role == rewrite_role)
    meter = parse_time_signature(voice.melody.time_signature)
    return tuple(
        event
        for event in voice.melody.events
        if event.pitch is not None
        and request.bar_start <= _bar_for_start(event.start, meter) <= request.bar_end
    )


def _bar_for_start(offset: Fraction, meter: TimeSignatureInfo) -> int:
    return int(offset // meter.bar_length) + 1


def _repeated_note_count(events: tuple[NoteEvent, ...]) -> int:
    count = 0
    for previous, current in pairwise(events):
        if previous.pitch == current.pitch and current.pitch is not None:
            count += 1
    return count


def _excess_leap_pressure(events: tuple[NoteEvent, ...]) -> float:
    pressure = 0.0
    for previous, current in pairwise(events):
        if previous.pitch is None or current.pitch is None:
            continue
        pressure += max(0, abs(current.pitch - previous.pitch) - 7)
    return pressure


def _bass_leap_pressure(events: tuple[NoteEvent, ...], rewrite_role: VoiceRole) -> float:
    if rewrite_role != "follower":
        return 0.0
    return _excess_leap_pressure(events)


def _cadence_motion_value(events: tuple[NoteEvent, ...]) -> float:
    if len(events) < 2:
        return 0.0
    previous = events[-2].pitch
    final = events[-1].pitch
    if previous is None or final is None:
        return 0.0
    interval = abs(final - previous)
    if interval in {1, 2}:
        return 1.0
    if interval in {3, 4, 5}:
        return 0.4
    return 0.0


def _lower_invention_components(
    parent: CanonCandidate,
    candidate: CanonCandidate,
    request: PolishRequest,
) -> dict[str, float]:
    parent_analysis = analyze_composition(parent)
    candidate_analysis = analyze_composition(candidate)
    parent_bass = parent_analysis.bass_support
    candidate_bass = candidate_analysis.bass_support
    if parent_bass is None or candidate_bass is None:
        return {
            "bass_root_support_reward": 0.0,
            "bass_foundation_reward": 0.0,
            "bass_independence_reward": 0.0,
            "static_bass_penalty": 0.0,
            "cadence_support_reward": 0.0,
        }
    return {
        "bass_root_support_reward": 4.0
        * (candidate_bass.root_support_proxy - parent_bass.root_support_proxy),
        "bass_foundation_reward": 3.0
        * (candidate_bass.sustained_foundation_score - parent_bass.sustained_foundation_score),
        "bass_independence_reward": 3.0
        * (candidate_bass.bass_independence_score - parent_bass.bass_independence_score),
        "static_bass_penalty": -float(
            sum(
                1
                for bar in candidate_bass.static_bars
                if request.bar_start <= bar <= request.bar_end
            )
        ),
        "cadence_support_reward": _cadence_value(candidate_analysis, request)
        - _cadence_value(parent_analysis, request),
    }


def _upper_invention_components(
    parent: CanonCandidate,
    candidate: CanonCandidate,
    request: PolishRequest,
    events: tuple[NoteEvent, ...],
) -> dict[str, float]:
    parent_analysis = analyze_composition(parent)
    candidate_analysis = analyze_composition(candidate)
    return {
        "phrase_warning_reduction_reward": float(
            _phrase_warning_count(parent_analysis, request)
            - _phrase_warning_count(candidate_analysis, request)
        ),
        "plateau_reduction_reward": float(
            _plateau_count(parent_analysis, request) - _plateau_count(candidate_analysis, request)
        ),
        "contour_variety_reward": _contour_variety(events),
        "cadence_clarity_reward": _cadence_value(candidate_analysis, request)
        - _cadence_value(parent_analysis, request),
    }


def _phrase_warning_count(analysis: CompositionAnalysis, request: PolishRequest) -> int:
    return sum(
        len(phrase.warnings)
        for phrase in analysis.phrases
        if _bars_overlap(phrase.bar_start, phrase.bar_end, request)
    )


def _plateau_count(analysis: CompositionAnalysis, request: PolishRequest) -> int:
    return sum(
        len(phrase.repeated_note_plateaus)
        for phrase in analysis.phrases
        if _bars_overlap(phrase.bar_start, phrase.bar_end, request)
    )


def _cadence_value(analysis: CompositionAnalysis, request: PolishRequest) -> float:
    candidates = [
        cadence
        for cadence in analysis.cadences
        if request.bar_start <= cadence.bar <= request.bar_end
    ]
    cadence = candidates[-1] if candidates else analysis.cadence
    if cadence is None:
        return 0.0
    strength_value = {"weak": 0.0, "moderate": 0.5, "strong": 1.0}[cadence.strength]
    type_bonus = 0.4 if cadence.cadence_type == "authentic_close_tendency" else 0.0
    return strength_value + type_bonus


def _contour_variety(events: tuple[NoteEvent, ...]) -> float:
    pitches = [event.pitch for event in events if event.pitch is not None]
    if not pitches:
        return 0.0
    return len(set(pitches)) / len(pitches)


def _bars_overlap(bar_start: int, bar_end: int, request: PolishRequest) -> bool:
    return bar_start <= request.bar_end and bar_end >= request.bar_start
