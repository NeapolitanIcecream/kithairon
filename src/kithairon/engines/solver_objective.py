"""Objective helpers for the CP-SAT relaxed canon solver."""

from __future__ import annotations

from dataclasses import dataclass

from kithairon.rules.consonance import CONSONANT_SIMPLE_SEMITONES

PitchRange = tuple[int, int]


@dataclass(frozen=True)
class SolverObjectiveConfig:
    follower_range: PitchRange = (36, 88)
    edit_weight: int = 100
    pitch_delta_weight: int = 2
    dissonance_weight: int = 12
    cadence_weight: int = 16
    consonant_semitones: frozenset[int] = CONSONANT_SIMPLE_SEMITONES
    cadential_consonances: frozenset[int] = frozenset({0, 3, 4, 7})


@dataclass(frozen=True)
class SolverPitchOption:
    pitch: int
    edit_cost: int
    consonance_cost: int
    cadence_cost: int

    @property
    def total_cost(self) -> int:
        return self.edit_cost + self.consonance_cost + self.cadence_cost


DEFAULT_SOLVER_OBJECTIVE = SolverObjectiveConfig()


def build_pitch_options(
    *,
    base_pitch: int,
    requirements: tuple[int, ...],
    weak_leader_pitches: tuple[int, ...],
    cadence_leader_pitch: int | None,
    objective: SolverObjectiveConfig = DEFAULT_SOLVER_OBJECTIVE,
) -> tuple[SolverPitchOption, ...]:
    options = tuple(
        _solver_pitch_option(
            pitch=pitch,
            base_pitch=base_pitch,
            weak_leader_pitches=weak_leader_pitches,
            cadence_leader_pitch=cadence_leader_pitch,
            objective=objective,
        )
        for pitch in _candidate_pitches(base_pitch, requirements, objective)
        if _meets_requirements(pitch, requirements, objective)
    )
    return tuple(sorted(options, key=lambda option: (option.total_cost, option.pitch)))


def _candidate_pitches(
    base_pitch: int,
    requirements: tuple[int, ...],
    objective: SolverObjectiveConfig,
) -> tuple[int, ...]:
    lower, upper = objective.follower_range
    nearby = range(max(lower, base_pitch - 12), min(upper, base_pitch + 12) + 1)
    if not requirements:
        return tuple(
            sorted(
                {base_pitch, base_pitch - 12, base_pitch + 12}.intersection(range(lower, upper + 1))
            )
        )
    return tuple(nearby)


def _solver_pitch_option(
    *,
    pitch: int,
    base_pitch: int,
    weak_leader_pitches: tuple[int, ...],
    cadence_leader_pitch: int | None,
    objective: SolverObjectiveConfig,
) -> SolverPitchOption:
    edited = pitch != base_pitch
    edit_cost = (objective.edit_weight if edited else 0) + abs(
        pitch - base_pitch
    ) * objective.pitch_delta_weight
    consonance_cost = objective.dissonance_weight * _dissonance_count(
        pitch,
        weak_leader_pitches,
        objective,
    )
    cadence_cost = _cadence_cost(pitch, cadence_leader_pitch, objective)
    return SolverPitchOption(
        pitch=pitch,
        edit_cost=edit_cost,
        consonance_cost=consonance_cost,
        cadence_cost=cadence_cost,
    )


def _meets_requirements(
    pitch: int,
    leader_pitches: tuple[int, ...],
    objective: SolverObjectiveConfig,
) -> bool:
    return all(
        _is_consonant_with_leader(pitch, leader_pitch, objective) for leader_pitch in leader_pitches
    )


def _dissonance_count(
    pitch: int,
    leader_pitches: tuple[int, ...],
    objective: SolverObjectiveConfig,
) -> int:
    return sum(
        0 if _is_consonant_with_leader(pitch, leader_pitch, objective) else 1
        for leader_pitch in leader_pitches
    )


def _cadence_cost(
    pitch: int,
    leader_pitch: int | None,
    objective: SolverObjectiveConfig,
) -> int:
    if leader_pitch is None:
        return 0
    return (
        0
        if abs(pitch - leader_pitch) % 12 in objective.cadential_consonances
        else objective.cadence_weight
    )


def _is_consonant_with_leader(
    pitch: int,
    leader_pitch: int,
    objective: SolverObjectiveConfig,
) -> bool:
    return abs(pitch - leader_pitch) % 12 in objective.consonant_semitones
