"""Small deterministic objective layer for first-pass phrase polish ranking."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from itertools import pairwise

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
