"""Deterministic symbolic musicality proxies for composition assistance."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from itertools import groupby, pairwise

from kithairon.ir import CanonCandidate, NoteEvent, Voice


@dataclass(frozen=True)
class MusicalityMetric:
    key: str
    label: str
    raw_value: float
    normalized_value: float
    weight: float
    higher_is_better: bool


@dataclass(frozen=True)
class MusicalityBreakdown:
    total: float
    metrics: tuple[MusicalityMetric, ...]

    @property
    def raw_values(self) -> Mapping[str, float]:
        return {metric.key: metric.raw_value for metric in self.metrics}

    @property
    def normalized_values(self) -> Mapping[str, float]:
        return {metric.key: metric.normalized_value for metric in self.metrics}

    @property
    def weights(self) -> Mapping[str, float]:
        return {metric.key: metric.weight for metric in self.metrics}


_WEIGHTS: Mapping[str, float] = {
    "repeated_note_density": 0.2,
    "repeated_note_plateau_count": 0.15,
    "melodic_leap_pressure": 0.2,
    "contour_variety": 0.15,
    "rhythmic_complementarity": 0.15,
    "bass_independence_proxy": 0.15,
}


def compute_musicality(candidate: CanonCandidate) -> MusicalityBreakdown:
    """Compute simple reproducible musicality proxies separate from hard-rule score."""
    voices = candidate.voices
    repeated_density = _repeated_note_density(voices)
    plateau_count = _plateau_count(voices)
    leap_pressure = _melodic_leap_pressure(voices)
    contour_variety = _contour_variety(voices)
    rhythmic_complementarity = _rhythmic_complementarity(voices)
    bass_independence = _bass_independence_proxy(candidate)

    metrics = (
        _metric(
            "repeated_note_density",
            "Repeated-note density",
            repeated_density,
            1.0 - _clamp01(repeated_density),
            higher_is_better=False,
        ),
        _metric(
            "repeated_note_plateau_count",
            "Repeated-note plateaus",
            float(plateau_count),
            1.0 - _clamp01(plateau_count / max(1.0, _pitched_event_count(voices) / 3.0)),
            higher_is_better=False,
        ),
        _metric(
            "melodic_leap_pressure",
            "Melodic leap pressure",
            leap_pressure,
            1.0 - _clamp01(leap_pressure / 12.0),
            higher_is_better=False,
        ),
        _metric(
            "contour_variety",
            "Contour variety",
            contour_variety,
            _clamp01(contour_variety),
            higher_is_better=True,
        ),
        _metric(
            "rhythmic_complementarity",
            "Rhythmic complementarity",
            rhythmic_complementarity,
            _clamp01(rhythmic_complementarity),
            higher_is_better=True,
        ),
        _metric(
            "bass_independence_proxy",
            "Bass independence proxy",
            bass_independence,
            _clamp01(bass_independence),
            higher_is_better=True,
        ),
    )
    total_weight = sum(metric.weight for metric in metrics)
    total = sum(metric.normalized_value * metric.weight for metric in metrics) / total_weight
    return MusicalityBreakdown(total=round(total * 100.0, 2), metrics=metrics)


def _metric(
    key: str,
    label: str,
    raw_value: float,
    normalized_value: float,
    *,
    higher_is_better: bool,
) -> MusicalityMetric:
    return MusicalityMetric(
        key=key,
        label=label,
        raw_value=round(raw_value, 4),
        normalized_value=round(_clamp01(normalized_value), 4),
        weight=_WEIGHTS[key],
        higher_is_better=higher_is_better,
    )


def _repeated_note_density(voices: tuple[Voice, ...]) -> float:
    repeated = 0
    transitions = 0
    for voice in voices:
        for previous, current in pairwise(_pitched_events(voice)):
            transitions += 1
            if previous.pitch == current.pitch:
                repeated += 1
    if transitions == 0:
        return 0.0
    return repeated / transitions


def _plateau_count(voices: tuple[Voice, ...]) -> int:
    count = 0
    for voice in voices:
        pitches = [event.pitch for event in _pitched_events(voice)]
        for pitch, group in groupby(pitches):
            if pitch is not None and len(list(group)) >= 3:
                count += 1
    return count


def _melodic_leap_pressure(voices: tuple[Voice, ...]) -> float:
    excess = 0.0
    transitions = 0
    for voice in voices:
        for previous, current in pairwise(_pitched_events(voice)):
            if previous.pitch is None or current.pitch is None:
                continue
            transitions += 1
            excess += max(0, abs(current.pitch - previous.pitch) - 7)
    if transitions == 0:
        return 0.0
    return excess / transitions


def _contour_variety(voices: tuple[Voice, ...]) -> float:
    values: list[float] = []
    for voice in voices:
        intervals = _melodic_intervals(voice)
        if not intervals:
            values.append(1.0)
            continue
        signs = {0 if interval == 0 else (1 if interval > 0 else -1) for interval in intervals}
        sign_changes = sum(
            1
            for previous, current in pairwise(intervals)
            if _interval_sign(previous) != _interval_sign(current)
        )
        sign_diversity = len(signs) / 3.0
        change_ratio = sign_changes / max(1, len(intervals) - 1)
        values.append((sign_diversity + change_ratio) / 2.0)
    return sum(values) / len(values) if values else 1.0


def _rhythmic_complementarity(voices: tuple[Voice, ...]) -> float:
    if len(voices) < 2:
        return 1.0
    onset_sets = [
        {event.start for event in voice.melody.events if event.pitch is not None}
        for voice in voices[:2]
    ]
    union = onset_sets[0] | onset_sets[1]
    if not union:
        return 1.0
    shared = onset_sets[0] & onset_sets[1]
    return 1.0 - (len(shared) / len(union))


def _bass_independence_proxy(candidate: CanonCandidate) -> float:
    follower = next((voice for voice in candidate.voices if voice.role == "follower"), None)
    if follower is None:
        return 1.0
    events = _pitched_events(follower)
    if len(events) <= 1:
        return 1.0
    pitches = [event.pitch for event in events if event.pitch is not None]
    unique_ratio = len(set(pitches)) / len(pitches) if pitches else 1.0
    repeat_penalty = _repeated_note_density((follower,))
    leap_pressure = _melodic_leap_pressure((follower,))
    smoothness = 1.0 - _clamp01(leap_pressure / 12.0)
    return (unique_ratio * 0.45) + ((1.0 - repeat_penalty) * 0.35) + (smoothness * 0.2)


def _pitched_event_count(voices: tuple[Voice, ...]) -> int:
    return sum(len(_pitched_events(voice)) for voice in voices)


def _pitched_events(voice: Voice) -> tuple[NoteEvent, ...]:
    return tuple(event for event in voice.melody.events if event.pitch is not None)


def _melodic_intervals(voice: Voice) -> tuple[int, ...]:
    intervals: list[int] = []
    for previous, current in pairwise(_pitched_events(voice)):
        if previous.pitch is not None and current.pitch is not None:
            intervals.append(current.pitch - previous.pitch)
    return tuple(intervals)


def _interval_sign(interval: int) -> int:
    if interval == 0:
        return 0
    return 1 if interval > 0 else -1


def _clamp01(value: float | Fraction) -> float:
    numeric = float(value)
    return max(0.0, min(1.0, numeric))
