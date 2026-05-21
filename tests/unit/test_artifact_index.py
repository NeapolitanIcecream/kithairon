from __future__ import annotations

import json
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from typing import Any, cast

import pytest

from kithairon.ir import CanonCandidate, Melody, NoteEvent, TransformSpec, Voice
from kithairon.visualization.artifact_index import (
    ArtifactIndexError,
    build_artifact_index,
    register_candidate_artifacts,
    resolve_candidate_artifact,
    resolve_run_artifact,
)


def test_build_artifact_index_separates_run_and_candidate_artifacts(tmp_path: Path) -> None:
    candidate = replace(
        _candidate("strict_0001"),
        metadata={
            "outputs": {
                "musicxml": "candidates/001.musicxml",
                "midi": "candidates/001.mid",
            }
        },
    )

    index = build_artifact_index(
        run_id="run-1",
        root=tmp_path,
        run_artifacts={
            "report": "report.md",
            "results": "results.json",
            "visualization": "visualization.json",
            "resolved_config": "resolved_config.toml",
        },
        candidates=(candidate,),
    )

    assert cast(dict[str, str], index["run_artifacts"])["report"] == "report.md"
    candidates = cast(dict[str, Any], index["candidates"])
    assert set(candidates) == {"strict_0001"}
    strict_artifacts = cast(dict[str, str | None], candidates["strict_0001"])
    assert strict_artifacts["musicxml"] == "candidates/001.musicxml"
    assert strict_artifacts["pdf"] is None


def test_resolve_run_artifact_returns_registered_path(tmp_path: Path) -> None:
    index_path = _write_index(
        tmp_path,
        {
            "run_artifacts": {"report": "report.md"},
            "candidates": {},
        },
    )

    assert resolve_run_artifact(index_path, "report") == tmp_path / "report.md"


def test_resolve_candidate_artifact_returns_registered_path(tmp_path: Path) -> None:
    index_path = _write_index(
        tmp_path,
        {
            "run_artifacts": {},
            "candidates": {"strict_0001": {"musicxml": "candidates/001.musicxml"}},
        },
    )

    assert (
        resolve_candidate_artifact(index_path, "strict_0001", "musicxml")
        == tmp_path / "candidates" / "001.musicxml"
    )


def test_resolve_artifact_rejects_path_traversal(tmp_path: Path) -> None:
    index_path = _write_index(
        tmp_path,
        {
            "run_artifacts": {"report": "../secret.md"},
            "candidates": {},
        },
    )

    with pytest.raises(ArtifactIndexError, match="escapes the run directory"):
        resolve_run_artifact(index_path, "report")


def test_resolve_artifact_rejects_missing_or_null_candidate_artifact(tmp_path: Path) -> None:
    index_path = _write_index(
        tmp_path,
        {
            "run_artifacts": {},
            "candidates": {"strict_0001": {"pdf": None}},
        },
    )

    with pytest.raises(ArtifactIndexError, match="Artifact is not registered"):
        resolve_candidate_artifact(index_path, "strict_0001", "pdf")


def test_register_candidate_artifacts_adds_safe_relative_paths(tmp_path: Path) -> None:
    index_path = _write_index(
        tmp_path,
        {
            "run_artifacts": {},
            "candidates": {},
        },
    )

    register_candidate_artifacts(
        index_path,
        "strict_0001_polish_001",
        {"musicxml": "experiments/experiment-0001/candidates/variant.musicxml"},
    )

    assert (
        resolve_candidate_artifact(index_path, "strict_0001_polish_001", "musicxml")
        == tmp_path / "experiments" / "experiment-0001" / "candidates" / "variant.musicxml"
    )


def test_register_candidate_artifacts_rejects_different_duplicate_candidate(
    tmp_path: Path,
) -> None:
    index_path = _write_index(
        tmp_path,
        {
            "run_artifacts": {},
            "candidates": {
                "strict_0001__polish__r001__001": {
                    "musicxml": "experiments/experiment-0001/candidates/variant.musicxml"
                }
            },
        },
    )

    with pytest.raises(ArtifactIndexError, match="already registered"):
        register_candidate_artifacts(
            index_path,
            "strict_0001__polish__r001__001",
            {"musicxml": "experiments/experiment-0002/candidates/variant.musicxml"},
        )


def test_register_candidate_artifacts_allows_idempotent_duplicate_registration(
    tmp_path: Path,
) -> None:
    artifacts = {"musicxml": "experiments/experiment-0001/candidates/variant.musicxml"}
    index_path = _write_index(
        tmp_path,
        {
            "run_artifacts": {},
            "candidates": {"strict_0001__polish__r001__001": artifacts},
        },
    )

    register_candidate_artifacts(index_path, "strict_0001__polish__r001__001", artifacts)

    assert (
        resolve_candidate_artifact(index_path, "strict_0001__polish__r001__001", "musicxml")
        == tmp_path / "experiments" / "experiment-0001" / "candidates" / "variant.musicxml"
    )


def _write_index(tmp_path: Path, payload: dict[str, object]) -> Path:
    index_path = tmp_path / "artifact_index.json"
    index_path.write_text(json.dumps({"run_id": "run-1", "root": str(tmp_path), **payload}))
    return index_path


def _candidate(candidate_id: str) -> CanonCandidate:
    voice = Voice(
        name="leader",
        role="leader",
        melody=Melody(
            events=(NoteEvent(id="n0001", pitch=60, start=Fraction(0), duration=Fraction(1)),),
            time_signature="4/4",
        ),
    )
    return CanonCandidate(
        id=candidate_id,
        voices=(voice, voice),
        transform_spec=TransformSpec(delay=Fraction(1)),
        engine="strict",
        strict_canon=True,
        score=100.0,
        violations=(),
    )
