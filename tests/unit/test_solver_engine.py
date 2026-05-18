from __future__ import annotations

from fractions import Fraction
from typing import cast

import pytest

from kithairon.config import GenerationConfig, KithaironConfig, SolverConfig
from kithairon.engines.solver import ensure_solver_available, generate_solver_candidates
from kithairon.errors import GenerationError
from kithairon.ir import Melody, NoteEvent


def _bad_melody() -> Melody:
    return Melody(
        events=(
            NoteEvent(id="n1", pitch=60, start=Fraction(0), duration=Fraction(1)),
            NoteEvent(id="n2", pitch=61, start=Fraction(1), duration=Fraction(1)),
            NoteEvent(id="n3", pitch=63, start=Fraction(2), duration=Fraction(1)),
            NoteEvent(id="n4", pitch=66, start=Fraction(3), duration=Fraction(1)),
        ),
        time_signature="4/4",
        tempo_bpm=92,
        key_hint="C major",
    )


def _solver_config() -> KithaironConfig:
    return KithaironConfig(
        generation=GenerationConfig(
            engine="solver",
            top_k=2,
            max_candidates=8,
            delays=(Fraction(1),),
            intervals=(-1, 1, 2),
            transforms=("transposition",),
        ),
        solver=SolverConfig(enabled=True, max_seconds=1.0, max_edited_notes=3, max_candidates_in=4),
    )


def test_solver_engine_outputs_relaxed_candidate_with_objective_details() -> None:
    candidates = generate_solver_candidates(_bad_melody(), _solver_config())

    assert candidates
    candidate = candidates[0]
    objective_details = cast(dict[str, object], candidate.metadata["objective_details"])

    assert candidate.engine == "solver"
    assert candidate.strict_canon is False
    assert candidate.metadata["edit_plan"]
    assert candidate.score > cast(float, candidate.metadata["base_strict_score"])
    assert objective_details["status"] in {"OPTIMAL", "FEASIBLE"}
    assert objective_details["max_time_seconds"] == 1.0
    assert "objective_value" in objective_details


def test_solver_engine_records_pitch_edit_plan() -> None:
    candidate = generate_solver_candidates(_bad_melody(), _solver_config())[0]
    edit_plan = cast(list[dict[str, object]], candidate.metadata["edit_plan"])

    assert edit_plan[0]["voice"] == "follower"
    assert edit_plan[0]["operation"] == "cp_sat_pitch_assignment"
    assert edit_plan[0]["from_pitch"] != edit_plan[0]["to_pitch"]
    assert edit_plan[0]["event_id"]


def test_solver_availability_check_reports_missing_optional_dependency() -> None:
    with pytest.raises(GenerationError) as raised:
        ensure_solver_available(importer=lambda: None)

    diagnostic = raised.value.to_diagnostic()
    assert diagnostic["code"] == "solver_unavailable"
    assert cast(dict[str, object], diagnostic["details"])["install_command"] == (
        "uv sync --extra solver"
    )
