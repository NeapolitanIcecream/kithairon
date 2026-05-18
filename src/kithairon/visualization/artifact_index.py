"""Artifact index creation for generated visualization runs."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import cast

from kithairon.ir import CanonCandidate

RUN_ARTIFACTS: tuple[str, ...] = ("report", "results", "visualization", "resolved_config")
CANDIDATE_ARTIFACTS: tuple[str, ...] = ("musicxml", "midi", "pdf", "svg", "png")


def build_artifact_index(
    *,
    run_id: str,
    root: Path,
    run_artifacts: Mapping[str, str],
    candidates: tuple[CanonCandidate, ...],
) -> dict[str, object]:
    """Build the JSON-safe artifact index for one generation run."""
    return {
        "run_id": run_id,
        "root": str(root),
        "run_artifacts": {
            kind: run_artifacts[kind] for kind in RUN_ARTIFACTS if kind in run_artifacts
        },
        "candidates": {
            candidate.id: _candidate_artifacts(candidate) for candidate in candidates
        },
    }


def _candidate_artifacts(candidate: CanonCandidate) -> dict[str, str | None]:
    outputs = _string_mapping(candidate.metadata.get("outputs"))
    return {kind: outputs.get(kind) for kind in CANDIDATE_ARTIFACTS}


def _string_mapping(value: object) -> Mapping[str, str]:
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, str] = {}
    for key, item in cast(Mapping[object, object], value).items():
        if isinstance(key, str) and isinstance(item, str):
            result[key] = item
    return result
