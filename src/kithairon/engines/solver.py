"""OR-Tools CP-SAT solver engine for relaxed canon candidates."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from importlib import import_module
from typing import Any

from kithairon.analysis import AnalysisContext, analyze_candidate
from kithairon.config import KithaironConfig, format_fraction
from kithairon.engines.strict import generate_strict_candidate_pool, transform_spec_to_dict
from kithairon.errors import GenerationError
from kithairon.ir import CanonCandidate, Melody, NoteEvent, RuleViolation, Voice
from kithairon.rules.consonance import CONSONANT_SIMPLE_SEMITONES
from kithairon.scoring import quality_status, rank_candidates, score_candidate

FOLLOWER_RANGE = (36, 88)
EDIT_WEIGHT = 100
PITCH_DELTA_WEIGHT = 2
DISSONANCE_WEIGHT = 12
CADENCE_WEIGHT = 16
CADENTIAL_CONSONANCES = frozenset({0, 3, 4, 7})


@dataclass(frozen=True)
class SolverPitchOption:
    pitch: int
    edit_cost: int
    consonance_cost: int
    cadence_cost: int

    @property
    def total_cost(self) -> int:
        return self.edit_cost + self.consonance_cost + self.cadence_cost


@dataclass(frozen=True)
class SolverNotePlan:
    event: NoteEvent
    options: tuple[SolverPitchOption, ...]
    choice_literals: tuple[Any, ...]


@dataclass(frozen=True)
class SolverOutcome:
    candidate: CanonCandidate | None
    details: Mapping[str, object]


@dataclass(frozen=True)
class SolverSolution:
    base_candidate: CanonCandidate
    follower: Melody
    note_plans: tuple[SolverNotePlan, ...]
    solver: Any
    details: Mapping[str, object]
    index: int


@dataclass(frozen=True)
class CPSATSolverEngine:
    config: KithaironConfig

    def generate(self, melody: Melody) -> tuple[CanonCandidate, ...]:
        cp_model = ensure_solver_available()
        strict_pool = generate_strict_candidate_pool(melody, self.config)
        base_candidates = _select_solver_bases(strict_pool, self.config)
        outcomes = tuple(
            self._solve_base_candidate(base_candidate, index, cp_model)
            for index, base_candidate in enumerate(base_candidates, 1)
        )
        candidates = tuple(
            outcome.candidate for outcome in outcomes if outcome.candidate is not None
        )
        return rank_candidates(candidates, top_k=self.config.generation.top_k)

    def _solve_base_candidate(
        self,
        base_candidate: CanonCandidate,
        index: int,
        cp_model: Any,
    ) -> SolverOutcome:
        context = analyze_candidate(base_candidate)
        model = cp_model.CpModel()
        note_plans = _build_note_plans(base_candidate, context, model)
        if not note_plans:
            return SolverOutcome(candidate=None, details={"status": "NO_VARIABLES"})

        model.add(
            sum(_edited_literal(plan) for plan in note_plans)
            <= self.config.solver.max_edited_notes
        )
        objective_terms = _objective_terms(note_plans)
        model.minimize(sum(objective_terms))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.config.solver.max_seconds
        status_code = solver.solve(model)
        status_name = str(solver.status_name(status_code))
        details = _solver_details(
            solver=solver,
            status_name=status_name,
            max_seconds=self.config.solver.max_seconds,
            objective_terms=len(objective_terms),
            note_count=len(note_plans),
        )
        if status_code not in {cp_model.OPTIMAL, cp_model.FEASIBLE}:
            return SolverOutcome(candidate=None, details=details)

        follower = _solution_to_melody(base_candidate.voices[1].melody, note_plans, solver)
        candidate = _score_solver_solution(
            SolverSolution(
                base_candidate=base_candidate,
                follower=follower,
                note_plans=note_plans,
                solver=solver,
                details=details,
                index=index,
            ),
            self.config,
        )
        if not candidate.metadata.get("edit_plan") or candidate.score <= base_candidate.score:
            return SolverOutcome(candidate=None, details=details)
        return SolverOutcome(candidate=candidate, details=details)


def generate_solver_candidates(
    melody: Melody,
    config: KithaironConfig,
) -> tuple[CanonCandidate, ...]:
    return CPSATSolverEngine(config).generate(melody)


def solver_available() -> bool:
    return _import_cp_model() is not None


def ensure_solver_available(
    importer: Callable[[], Any | None] = lambda: _import_cp_model(),
) -> Any:
    cp_model = importer()
    if cp_model is None:
        raise GenerationError(
            "OR-Tools solver dependency is not installed. Run uv sync --extra solver.",
            code="solver_unavailable",
            details={
                "extra": "solver",
                "package": "ortools",
                "install_command": "uv sync --extra solver",
            },
        )
    return cp_model


def _import_cp_model() -> Any | None:
    try:
        return import_module("ortools.sat.python.cp_model")
    except ImportError:
        return None


def _select_solver_bases(
    strict_pool: tuple[CanonCandidate, ...],
    config: KithaironConfig,
) -> tuple[CanonCandidate, ...]:
    repairable = tuple(candidate for candidate in strict_pool if _repairable_violations(candidate))
    candidate_pool = repairable or strict_pool
    return tuple(
        sorted(
            candidate_pool,
            key=lambda candidate: (-len(candidate.violations), -candidate.score, candidate.id),
        )[: config.solver.max_candidates_in]
    )


def _build_note_plans(
    base_candidate: CanonCandidate,
    context: AnalysisContext,
    model: Any,
) -> tuple[SolverNotePlan, ...]:
    requirements = _strong_consonance_requirements(context)
    weak_context = _weak_consonance_context(context)
    cadence_context = _cadence_context(context)
    plans: list[SolverNotePlan] = []
    for event in base_candidate.voices[1].melody.events:
        if event.pitch is None:
            continue
        options = _pitch_options(
            event=event,
            requirements=requirements.get(event.id, ()),
            weak_leader_pitches=weak_context.get(event.id, ()),
            cadence_leader_pitch=cadence_context.get(event.id),
        )
        if not options:
            return ()
        plans.append(_note_plan_for_event(model, event, options))
    return tuple(plans)


def _note_plan_for_event(
    model: Any,
    event: NoteEvent,
    options: tuple[SolverPitchOption, ...],
) -> SolverNotePlan:
    literals = tuple(
        model.new_bool_var(f"choose_{event.id}_{index}") for index, _ in enumerate(options)
    )
    model.add(sum(literals) == 1)
    return SolverNotePlan(event=event, options=options, choice_literals=literals)


def _pitch_options(
    *,
    event: NoteEvent,
    requirements: tuple[int, ...],
    weak_leader_pitches: tuple[int, ...],
    cadence_leader_pitch: int | None,
) -> tuple[SolverPitchOption, ...]:
    assert event.pitch is not None
    candidate_pitches = _candidate_pitches(event.pitch, requirements)
    options = tuple(
        _solver_pitch_option(
            pitch=pitch,
            base_pitch=event.pitch,
            weak_leader_pitches=weak_leader_pitches,
            cadence_leader_pitch=cadence_leader_pitch,
        )
        for pitch in candidate_pitches
        if _meets_requirements(pitch, requirements)
    )
    return tuple(sorted(options, key=lambda option: (option.total_cost, option.pitch)))


def _candidate_pitches(base_pitch: int, requirements: tuple[int, ...]) -> tuple[int, ...]:
    lower, upper = FOLLOWER_RANGE
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
) -> SolverPitchOption:
    edited = pitch != base_pitch
    edit_cost = (EDIT_WEIGHT if edited else 0) + abs(pitch - base_pitch) * PITCH_DELTA_WEIGHT
    consonance_cost = DISSONANCE_WEIGHT * _dissonance_count(pitch, weak_leader_pitches)
    cadence_cost = _cadence_cost(pitch, cadence_leader_pitch)
    return SolverPitchOption(
        pitch=pitch,
        edit_cost=edit_cost,
        consonance_cost=consonance_cost,
        cadence_cost=cadence_cost,
    )


def _objective_terms(note_plans: tuple[SolverNotePlan, ...]) -> tuple[Any, ...]:
    return tuple(
        option.total_cost * literal
        for plan in note_plans
        for option, literal in zip(plan.options, plan.choice_literals, strict=True)
    )


def _edited_literal(plan: SolverNotePlan) -> Any:
    base_index = next(
        (
            index
            for index, option in enumerate(plan.options)
            if option.pitch == plan.event.pitch
        ),
        None,
    )
    if base_index is None:
        return 1
    return 1 - plan.choice_literals[base_index]


def _solution_to_melody(
    melody: Melody,
    note_plans: tuple[SolverNotePlan, ...],
    solver: Any,
) -> Melody:
    pitch_by_event_id = {
        plan.event.id: _selected_option(plan, solver).pitch for plan in note_plans
    }
    return replace(
        melody,
        events=tuple(
            replace(event, pitch=pitch_by_event_id[event.id])
            if event.id in pitch_by_event_id and event.pitch is not None
            else event
            for event in melody.events
        ),
    )


def _score_solver_solution(
    solution: SolverSolution,
    config: KithaironConfig,
) -> CanonCandidate:
    candidate = CanonCandidate(
        id=f"solver_{solution.index:04d}_{solution.base_candidate.id}",
        voices=(
            solution.base_candidate.voices[0],
            Voice(name="follower", melody=solution.follower, role="follower"),
        ),
        transform_spec=solution.base_candidate.transform_spec,
        engine="solver",
        strict_canon=False,
        score=0.0,
        violations=(),
        metadata=_solver_candidate_metadata(solution),
    )
    scored = score_candidate(candidate, quality=config.quality)
    return replace(
        scored,
        metadata={
            **scored.metadata,
            "quality_status": quality_status(scored.score, config.quality),
        },
    )


def _solver_candidate_metadata(solution: SolverSolution) -> dict[str, object]:
    return {
        "base_strict_candidate_id": solution.base_candidate.id,
        "base_strict_score": solution.base_candidate.score,
        "base_transform": transform_spec_to_dict(solution.base_candidate.transform_spec),
        "bad_windows": _violation_summaries(solution.base_candidate.violations),
        "edit_plan": _edit_plan(solution.note_plans, solution.solver),
        "objective_details": solution.details,
    }


def _edit_plan(note_plans: tuple[SolverNotePlan, ...], solver: Any) -> list[dict[str, object]]:
    edits: list[dict[str, object]] = []
    for plan in note_plans:
        option = _selected_option(plan, solver)
        if option.pitch == plan.event.pitch:
            continue
        assert plan.event.pitch is not None
        edits.append(
            {
                "voice": "follower",
                "event_id": plan.event.id,
                "operation": "cp_sat_pitch_assignment",
                "from_pitch": plan.event.pitch,
                "to_pitch": option.pitch,
                "delta": option.pitch - int(plan.event.pitch),
                "cost": option.total_cost,
            }
        )
    return edits


def _selected_option(plan: SolverNotePlan, solver: Any) -> SolverPitchOption:
    for option, literal in zip(plan.options, plan.choice_literals, strict=True):
        if solver.value(literal) == 1:
            return option
    return plan.options[0]


def _solver_details(
    *,
    solver: Any,
    status_name: str,
    max_seconds: float,
    objective_terms: int,
    note_count: int,
) -> dict[str, object]:
    return {
        "status": status_name,
        "objective_value": float(solver.objective_value),
        "best_objective_bound": float(solver.best_objective_bound),
        "wall_time_seconds": float(solver.wall_time),
        "max_time_seconds": max_seconds,
        "conflicts": int(solver.num_conflicts),
        "branches": int(solver.num_branches),
        "note_variables": note_count,
        "objective_terms": objective_terms,
        "hard_constraints": ["strong_beat_consonance", "range", "max_edited_notes"],
        "soft_objectives": ["edit_distance", "consonance_preference", "cadence_stability"],
    }


def _strong_consonance_requirements(context: AnalysisContext) -> dict[str, tuple[int, ...]]:
    requirements: dict[str, list[int]] = {}
    for verticality in context.verticalities:
        event_id = verticality.event_ids.get("follower")
        leader_pitch = verticality.pitches.get("leader")
        if event_id is None or leader_pitch is None:
            continue
        if verticality.beat_strength in {"strong", "medium"}:
            requirements.setdefault(event_id, []).append(leader_pitch)
    return {event_id: tuple(pitches) for event_id, pitches in requirements.items()}


def _weak_consonance_context(context: AnalysisContext) -> dict[str, tuple[int, ...]]:
    weak_context: dict[str, list[int]] = {}
    for verticality in context.verticalities:
        event_id = verticality.event_ids.get("follower")
        leader_pitch = verticality.pitches.get("leader")
        if event_id is None or leader_pitch is None or verticality.beat_strength != "weak":
            continue
        weak_context.setdefault(event_id, []).append(leader_pitch)
    return {event_id: tuple(pitches) for event_id, pitches in weak_context.items()}


def _cadence_context(context: AnalysisContext) -> dict[str, int]:
    if not context.verticalities:
        return {}
    verticality = context.verticalities[-1]
    event_id = verticality.event_ids.get("follower")
    leader_pitch = verticality.pitches.get("leader")
    if event_id is None or leader_pitch is None:
        return {}
    return {event_id: leader_pitch}


def _meets_requirements(pitch: int, leader_pitches: tuple[int, ...]) -> bool:
    return all(_is_consonant_with_leader(pitch, leader_pitch) for leader_pitch in leader_pitches)


def _dissonance_count(pitch: int, leader_pitches: tuple[int, ...]) -> int:
    return sum(
        0 if _is_consonant_with_leader(pitch, leader_pitch) else 1
        for leader_pitch in leader_pitches
    )


def _cadence_cost(pitch: int, leader_pitch: int | None) -> int:
    if leader_pitch is None:
        return 0
    return 0 if abs(pitch - leader_pitch) % 12 in CADENTIAL_CONSONANCES else CADENCE_WEIGHT


def _is_consonant_with_leader(pitch: int, leader_pitch: int) -> bool:
    return abs(pitch - leader_pitch) % 12 in CONSONANT_SIMPLE_SEMITONES


def _repairable_violations(candidate: CanonCandidate) -> tuple[RuleViolation, ...]:
    follower_event_ids = frozenset(event.id for event in candidate.voices[1].melody.events)
    return tuple(
        violation
        for violation in candidate.violations
        if follower_event_ids.intersection(violation.event_ids)
    )


def _violation_summaries(violations: tuple[RuleViolation, ...]) -> list[dict[str, object]]:
    return [
        {
            "rule_id": violation.rule_id,
            "severity": violation.severity,
            "penalty": violation.penalty,
            "bar": violation.bar,
            "beat": format_fraction(violation.beat) if violation.beat is not None else None,
            "event_ids": list(violation.event_ids),
        }
        for violation in violations
    ]
