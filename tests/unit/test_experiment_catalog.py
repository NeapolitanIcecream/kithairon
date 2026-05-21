from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

import pytest

from kithairon.errors import OutputError
from kithairon.experiments.catalog import load_candidate_catalog
from kithairon.experiments.store import create_experiment
from kithairon.ir import CanonCandidate, Melody, NoteEvent, TransformSpec, Voice
from kithairon.visualization.materialize import materialize_candidate
from kithairon.visualization.models import CandidateVizDTO, RunSummaryDTO


def test_candidate_catalog_merges_run_candidates_and_experiment_variants(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run-1"
    run_dir.mkdir()
    _write_artifact_index(run_dir)
    base = materialize_candidate(_candidate("strict_0001"))
    variant = materialize_candidate(
        _candidate("strict_0001_polish_001", parent_candidate_id="strict_0001")
    )
    _write_visualization(run_dir, [base])
    experiment = create_experiment(
        run_dir,
        source_candidate_id=base.candidate_id,
        source_request={"bar_start": 1, "bar_end": 1},
        candidates=[variant],
    )

    catalog = load_candidate_catalog(run_dir)

    assert [entry.candidate.candidate_id for entry in catalog.entries] == [
        "strict_0001",
        "strict_0001_polish_001",
    ]
    run_entry = catalog.get("strict_0001")
    experiment_entry = catalog.get("strict_0001_polish_001")
    assert run_entry.source_kind == "run"
    assert run_entry.source_experiment_id is None
    assert run_entry.parent_candidate_id is None
    assert experiment_entry.source_kind == "experiment"
    assert experiment_entry.source_experiment_id == experiment.experiment_id
    assert experiment_entry.parent_candidate_id == "strict_0001"
    assert experiment_entry.candidate.metadata["source_kind"] == "experiment"
    assert experiment_entry.candidate.metadata["source_experiment_id"] == experiment.experiment_id
    assert catalog.get("strict_0001_polish_001").candidate.candidate_id == (
        "strict_0001_polish_001"
    )


def test_candidate_catalog_rejects_duplicate_candidate_ids(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-1"
    run_dir.mkdir()
    _write_artifact_index(run_dir)
    base = materialize_candidate(_candidate("strict_0001"))
    duplicate_variant = materialize_candidate(
        _candidate("strict_0001", parent_candidate_id="strict_0001")
    )
    _write_visualization(run_dir, [base])
    create_experiment(
        run_dir,
        source_candidate_id=base.candidate_id,
        source_request={"bar_start": 1, "bar_end": 1},
        candidates=[duplicate_variant],
    )

    with pytest.raises(OutputError, match="Duplicate candidate id"):
        load_candidate_catalog(run_dir)


def _write_visualization(run_dir: Path, candidates: list[CandidateVizDTO]) -> None:
    summary = RunSummaryDTO(
        run_id=run_dir.name,
        input_name="fixture.musicxml",
        created_at="2026-05-20T00:00:00Z",
        config_summary={},
        candidates=candidates,
    )
    (run_dir / "visualization.json").write_text(
        json.dumps(summary.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )


def _write_artifact_index(run_dir: Path) -> None:
    (run_dir / "artifact_index.json").write_text(
        json.dumps(
            {"run_id": run_dir.name, "root": str(run_dir), "run_artifacts": {}, "candidates": {}}
        ),
        encoding="utf-8",
    )


def _candidate(candidate_id: str, *, parent_candidate_id: str | None = None) -> CanonCandidate:
    leader = Voice(
        name="leader",
        role="leader",
        melody=Melody(
            events=(
                NoteEvent(id="l1", pitch=60, start=Fraction(0), duration=Fraction(1)),
                NoteEvent(id="l2", pitch=62, start=Fraction(1), duration=Fraction(1)),
            ),
            time_signature="4/4",
        ),
    )
    follower = Voice(
        name="follower",
        role="follower",
        melody=Melody(
            events=(
                NoteEvent(id="f1", pitch=48, start=Fraction(1), duration=Fraction(1)),
                NoteEvent(id="f2", pitch=50, start=Fraction(2), duration=Fraction(1)),
            ),
            time_signature="4/4",
        ),
    )
    metadata: dict[str, object] = {}
    if parent_candidate_id is not None:
        metadata["parent_candidate_id"] = parent_candidate_id
    return CanonCandidate(
        id=candidate_id,
        voices=(leader, follower),
        transform_spec=TransformSpec(delay=Fraction(1), interval=-12),
        engine="strict",
        strict_canon=False,
        score=88.0,
        violations=(),
        metadata=metadata,
    )
