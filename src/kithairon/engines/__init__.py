"""Generation engines."""

from kithairon.engines.auto import AutoEngine, generate_auto_candidates
from kithairon.engines.repair import BeamRepairEngine, EditAction, generate_repair_candidates
from kithairon.engines.solver import (
    CPSATSolverEngine,
    ensure_solver_available,
    generate_solver_candidates,
    solver_available,
)
from kithairon.engines.strict import (
    StrictEngine,
    generate_strict_candidate_pool,
    generate_strict_candidates,
    transform_spec_to_dict,
)

__all__ = [
    "AutoEngine",
    "BeamRepairEngine",
    "CPSATSolverEngine",
    "EditAction",
    "StrictEngine",
    "ensure_solver_available",
    "generate_auto_candidates",
    "generate_repair_candidates",
    "generate_solver_candidates",
    "generate_strict_candidate_pool",
    "generate_strict_candidates",
    "solver_available",
    "transform_spec_to_dict",
]
