"""Candidate identity allocation for local polish variants."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from kithairon.errors import PolishError
from kithairon.visualization.artifact_index import ArtifactIndexError, load_artifact_index

_SAFE_FRAGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def allocate_polish_request_token(run_dir: Path, *, parent_id: str) -> str:
    """Allocate the next persisted request token for a parent candidate."""
    _validate_safe_fragment(parent_id)
    existing_ids = _persisted_candidate_ids(run_dir)
    pattern = re.compile(rf"^{re.escape(parent_id)}__polish__(r\d{{3}})__\d{{3}}$")
    highest = 0
    for candidate_id in existing_ids:
        match = pattern.match(candidate_id)
        if match is None:
            continue
        highest = max(highest, int(match.group(1)[1:]))
    return f"r{highest + 1:03d}"


def derived_candidate_id(parent_id: str, request_token: str, rank: int) -> str:
    """Return a path-safe, request-scoped derived candidate id."""
    _validate_safe_fragment(parent_id)
    _validate_safe_fragment(request_token)
    if rank < 1:
        raise PolishError(
            "Derived candidate rank must be positive.",
            code="invalid_derived_candidate_rank",
            details={"rank": rank},
        )
    return f"{parent_id}__polish__{request_token}__{rank:03d}"


def _persisted_candidate_ids(run_dir: Path) -> set[str]:
    index_path = run_dir / "artifact_index.json"
    if not index_path.exists():
        return set()
    try:
        index = load_artifact_index(index_path)
    except ArtifactIndexError as exc:
        raise PolishError(
            "Could not allocate a polish request token from the artifact index.",
            code="polish_request_token_allocation_failed",
            details={"path": str(index_path), "error": str(exc)},
        ) from exc
    candidates = index.get("candidates")
    if not isinstance(candidates, Mapping):
        return set()
    return {key for key in cast(Mapping[object, object], candidates) if isinstance(key, str)}


def _validate_safe_fragment(value: str) -> None:
    if _SAFE_FRAGMENT.fullmatch(value) is None:
        raise PolishError(
            "Candidate id fragment is not safe.",
            code="unsafe_candidate_id_fragment",
            details={"value": value},
        )
