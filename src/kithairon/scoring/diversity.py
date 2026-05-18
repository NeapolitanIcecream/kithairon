"""Diversity-aware candidate ranking."""

from __future__ import annotations

from dataclasses import replace

from kithairon.ir import CanonCandidate, TransformSpec


def rank_candidates(
    candidates: tuple[CanonCandidate, ...],
    *,
    top_k: int,
    diversity_penalty: float = 3.0,
) -> tuple[CanonCandidate, ...]:
    remaining = sorted(candidates, key=lambda candidate: (-candidate.score, candidate.id))
    selected: list[CanonCandidate] = []

    while remaining and len(selected) < top_k:
        best_candidate = max(
            remaining,
            key=lambda candidate: (
                _diverse_rank_score(candidate, selected, diversity_penalty),
                candidate.score,
                candidate.id,
            ),
        )
        remaining.remove(best_candidate)
        rank_score = _diverse_rank_score(best_candidate, selected, diversity_penalty)
        selected.append(_with_rank_metadata(best_candidate, len(selected) + 1, rank_score))

    return tuple(selected)


def _diverse_rank_score(
    candidate: CanonCandidate,
    selected: list[CanonCandidate],
    diversity_penalty: float,
) -> float:
    return candidate.score - (
        diversity_penalty
        * sum(
            _transform_similarity(candidate.transform_spec, selected_candidate.transform_spec)
            for selected_candidate in selected
        )
    )


def _transform_similarity(first: TransformSpec, second: TransformSpec) -> int:
    similarity = 0
    if first.transform_mode == second.transform_mode:
        similarity += 1
    if first.interval == second.interval:
        similarity += 1
    if first.delay == second.delay:
        similarity += 1
    return similarity


def _with_rank_metadata(
    candidate: CanonCandidate,
    rank: int,
    rank_score: float,
) -> CanonCandidate:
    return replace(
        candidate,
        metadata={
            **candidate.metadata,
            "rank": rank,
            "diverse_rank_score": round(rank_score, 2),
        },
    )
