"""Artifact index creation for generated visualization runs."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from kithairon.ir import CanonCandidate

RUN_ARTIFACTS: tuple[str, ...] = ("report", "results", "visualization", "resolved_config")
CANDIDATE_ARTIFACTS: tuple[str, ...] = ("musicxml", "midi", "pdf", "svg", "png")


class ArtifactIndexError(ValueError):
    """Raised when an artifact index is missing, malformed, or unsafe."""


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


def load_artifact_index(index_path: Path) -> Mapping[str, object]:
    """Load an artifact index from disk."""
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ArtifactIndexError(f"Could not read artifact index: {index_path}") from exc
    except json.JSONDecodeError as exc:
        raise ArtifactIndexError(f"Artifact index is not valid JSON: {index_path}") from exc

    if not isinstance(payload, Mapping):
        raise ArtifactIndexError("Artifact index must be a JSON object.")
    mapped = cast(Mapping[object, object], payload)
    return {key: item for key, item in mapped.items() if isinstance(key, str)}


def resolve_run_artifact(index_path: Path, kind: str) -> Path:
    """Resolve a run-level artifact path from an index."""
    index = load_artifact_index(index_path)
    run_artifacts = _object_mapping(index.get("run_artifacts"))
    relative_path = _required_relative_artifact(run_artifacts, kind)
    return _resolve_relative_artifact(index_path.parent, relative_path)


def resolve_candidate_artifact(index_path: Path, candidate_id: str, kind: str) -> Path:
    """Resolve a candidate-level artifact path from an index."""
    index = load_artifact_index(index_path)
    candidates = _object_mapping(index.get("candidates"))
    candidate = _object_mapping(candidates.get(candidate_id))
    if not candidate:
        raise ArtifactIndexError(f"Candidate artifact entry is not registered: {candidate_id}")
    relative_path = _required_relative_artifact(candidate, kind)
    return _resolve_relative_artifact(index_path.parent, relative_path)


def update_candidate_artifacts(
    index_path: Path,
    candidate_id: str,
    artifacts: Mapping[str, str],
) -> None:
    """Update candidate artifact entries in an existing artifact index."""
    index = dict(load_artifact_index(index_path))
    candidates = dict(_object_mapping(index.get("candidates")))
    candidate = dict(_object_mapping(candidates.get(candidate_id)))
    if not candidate:
        raise ArtifactIndexError(f"Candidate artifact entry is not registered: {candidate_id}")
    for kind, relative_path in artifacts.items():
        _resolve_relative_artifact(index_path.parent, relative_path)
        candidate[kind] = relative_path
    candidates[candidate_id] = candidate
    index["candidates"] = candidates
    index_path.write_text(
        json.dumps(index, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _candidate_artifacts(candidate: CanonCandidate) -> dict[str, str | None]:
    outputs = _string_mapping(candidate.metadata.get("outputs"))
    return {kind: outputs.get(kind) for kind in CANDIDATE_ARTIFACTS}


def _required_relative_artifact(artifacts: Mapping[str, object], kind: str) -> str:
    value = artifacts.get(kind)
    if value is None:
        raise ArtifactIndexError(f"Artifact is not registered: {kind}")
    if not isinstance(value, str) or not value:
        raise ArtifactIndexError(f"Artifact path must be a non-empty string: {kind}")
    return value


def _resolve_relative_artifact(root: Path, relative_path: str) -> Path:
    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise ArtifactIndexError("Artifact paths must be relative to the run directory.")

    resolved_root = root.resolve()
    resolved_path = (root / candidate).resolve()
    if not resolved_path.is_relative_to(resolved_root):
        raise ArtifactIndexError("Artifact path escapes the run directory.")
    return resolved_path


def _object_mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        return {}
    mapped = cast(Mapping[object, object], value)
    return {key: item for key, item in mapped.items() if isinstance(key, str)}


def _string_mapping(value: object) -> Mapping[str, str]:
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, str] = {}
    for key, item in cast(Mapping[object, object], value).items():
        if isinstance(key, str) and isinstance(item, str):
            result[key] = item
    return result
