from __future__ import annotations

from kithairon.engines.solver_objective import (
    DEFAULT_SOLVER_OBJECTIVE,
    SolverObjectiveConfig,
    build_pitch_options,
)


def test_pitch_options_without_requirements_keep_base_and_octaves() -> None:
    options = build_pitch_options(
        base_pitch=60,
        requirements=(),
        weak_leader_pitches=(),
        cadence_leader_pitch=None,
    )

    assert tuple(option.pitch for option in options) == (60, 48, 72)
    assert all(option.consonance_cost == 0 for option in options)


def test_pitch_options_with_requirements_only_keep_consonant_pitches() -> None:
    options = build_pitch_options(
        base_pitch=61,
        requirements=(60,),
        weak_leader_pitches=(),
        cadence_leader_pitch=None,
    )

    assert options
    assert all(
        abs(option.pitch - 60) % 12 in DEFAULT_SOLVER_OBJECTIVE.consonant_semitones
        for option in options
    )


def test_pitch_option_costs_are_configurable() -> None:
    objective = SolverObjectiveConfig(
        edit_weight=10,
        pitch_delta_weight=1,
        dissonance_weight=5,
        cadence_weight=7,
    )

    options = build_pitch_options(
        base_pitch=60,
        requirements=(60,),
        weak_leader_pitches=(61,),
        cadence_leader_pitch=61,
        objective=objective,
    )
    edited_unison = next(option for option in options if option.pitch == 48)

    assert edited_unison.edit_cost == 22
    assert edited_unison.consonance_cost == 5
    assert edited_unison.cadence_cost == 7
    assert edited_unison.total_cost == 34
