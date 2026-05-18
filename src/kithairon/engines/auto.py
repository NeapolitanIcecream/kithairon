"""Automatic engine orchestration across strict, repair, and solver candidates."""

from __future__ import annotations

from dataclasses import dataclass, replace

from kithairon.config import KithaironConfig
from kithairon.engines.repair import generate_repair_candidates
from kithairon.engines.solver import generate_solver_candidates, solver_available
from kithairon.engines.strict import StrictEngine
from kithairon.ir import CanonCandidate, Melody
from kithairon.scoring import rank_candidates


@dataclass(frozen=True)
class FallbackContext:
    strict_summary: dict[str, object]
    repair_candidates: tuple[CanonCandidate, ...]
    solver_candidates: tuple[CanonCandidate, ...]
    repair_triggered: bool
    solver_triggered: bool
    solver_available_now: bool


def generate_auto_candidates(
    melody: Melody,
    config: KithaironConfig,
) -> tuple[CanonCandidate, ...]:
    return AutoEngine(config).generate(melody)


class AutoEngine:
    def __init__(self, config: KithaironConfig) -> None:
        self.config = config

    def generate(self, melody: Melody) -> tuple[CanonCandidate, ...]:
        strict_pool = StrictEngine(self.config).generate_pool(melody)
        strict_candidates = rank_candidates(strict_pool, top_k=self.config.generation.top_k)
        strict_summary = _strict_summary(strict_pool)
        should_repair = _should_trigger_repair(strict_summary, self.config)

        repair_candidates = (
            generate_repair_candidates(melody, self.config) if should_repair else ()
        )
        should_solver = _should_trigger_solver(repair_candidates, should_repair, self.config)
        solver_candidates = (
            generate_solver_candidates(melody, self.config)
            if should_solver and solver_available()
            else ()
        )
        fallback_path = _fallback_path(
            FallbackContext(
                strict_summary=strict_summary,
                repair_candidates=repair_candidates,
                solver_candidates=solver_candidates,
                repair_triggered=should_repair,
                solver_triggered=should_solver and bool(solver_candidates),
                solver_available_now=solver_available(),
            ),
            self.config,
        )
        return _select_auto_candidates(
            strict_candidates=strict_candidates,
            repair_candidates=repair_candidates,
            solver_candidates=solver_candidates,
            fallback_path=fallback_path,
            top_k=self.config.generation.top_k,
        )


def _strict_summary(strict_pool: tuple[CanonCandidate, ...]) -> dict[str, object]:
    scores = [candidate.score for candidate in strict_pool]
    if not scores:
        return {"best_score": 0.0, "average_score": 0.0, "below_repair_threshold": 0}
    return {
        "best_score": max(scores),
        "average_score": round(sum(scores) / len(scores), 2),
        "candidate_count": len(scores),
    }


def _should_trigger_repair(
    strict_summary: dict[str, object],
    config: KithaironConfig,
) -> bool:
    best_score = _summary_float(strict_summary, "best_score")
    average_score = _summary_float(strict_summary, "average_score")
    threshold = config.quality.auto_repair_threshold
    return best_score < threshold or average_score < threshold


def _should_trigger_solver(
    repair_candidates: tuple[CanonCandidate, ...],
    repair_triggered: bool,
    config: KithaironConfig,
) -> bool:
    if not repair_triggered:
        return False
    best_repair_score = max((candidate.score for candidate in repair_candidates), default=0.0)
    return best_repair_score < config.quality.auto_solver_threshold


def _fallback_path(
    context: FallbackContext,
    config: KithaironConfig,
) -> dict[str, object]:
    return {
        "strict": {
            **context.strict_summary,
            "auto_repair_threshold": config.quality.auto_repair_threshold,
        },
        "repair": {
            "triggered": context.repair_triggered,
            "candidate_count": len(context.repair_candidates),
            "best_score": _best_score(context.repair_candidates),
        },
        "solver": {
            "triggered": context.solver_triggered,
            "available": context.solver_available_now,
            "candidate_count": len(context.solver_candidates),
            "best_score": _best_score(context.solver_candidates),
            "auto_solver_threshold": config.quality.auto_solver_threshold,
        },
        "reason": _fallback_reason(
            context.strict_summary,
            context.repair_triggered,
            context.solver_triggered,
            config,
        ),
    }


def _fallback_reason(
    strict_summary: dict[str, object],
    repair_triggered: bool,
    solver_triggered: bool,
    config: KithaironConfig,
) -> str:
    if solver_triggered:
        return "repair remained below solver threshold; solver fallback was used"
    if repair_triggered:
        return "strict pool average was below repair threshold; repair fallback was used"
    return (
        "strict pool passed auto repair threshold "
        f"({strict_summary['average_score']} >= {config.quality.auto_repair_threshold})"
    )


def _select_auto_candidates(
    *,
    strict_candidates: tuple[CanonCandidate, ...],
    repair_candidates: tuple[CanonCandidate, ...],
    solver_candidates: tuple[CanonCandidate, ...],
    fallback_path: dict[str, object],
    top_k: int,
) -> tuple[CanonCandidate, ...]:
    fallback_candidates = repair_candidates + solver_candidates
    ranked = list(rank_candidates(strict_candidates + fallback_candidates, top_k=top_k))
    if fallback_candidates and all(candidate.engine == "strict" for candidate in ranked):
        ranked = ranked[: max(0, top_k - 1)]
        ranked.append(max(fallback_candidates, key=lambda candidate: candidate.score))
    return _with_auto_metadata(tuple(ranked[:top_k]), fallback_path)


def _with_auto_metadata(
    candidates: tuple[CanonCandidate, ...],
    fallback_path: dict[str, object],
) -> tuple[CanonCandidate, ...]:
    return tuple(
        replace(
            candidate,
            metadata={
                **candidate.metadata,
                "rank": rank,
                "fallback_path": fallback_path,
            },
        )
        for rank, candidate in enumerate(candidates, start=1)
    )


def _best_score(candidates: tuple[CanonCandidate, ...]) -> float | None:
    if not candidates:
        return None
    return max(candidate.score for candidate in candidates)


def _summary_float(summary: dict[str, object], key: str) -> float:
    value = summary[key]
    if isinstance(value, int | float):
        return float(value)
    raise TypeError(f"strict summary field is not numeric: {key}")
