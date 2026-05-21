"""Run-local experiment persistence for candidate polish results."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from pydantic import ValidationError

from kithairon.errors import OutputError
from kithairon.export import write_candidate_exports
from kithairon.polish.apply import candidate_from_dto
from kithairon.visualization.artifact_index import ArtifactIndexError, register_candidate_artifacts
from kithairon.visualization.materialize import materialize_candidate
from kithairon.visualization.models import (
    CandidateVizDTO,
    ExperimentDTO,
    ExperimentPatchDTO,
    ExperimentVariantDTO,
)


def create_experiment(
    run_dir: Path,
    *,
    source_candidate_id: str,
    source_request: dict[str, object],
    candidates: list[CandidateVizDTO],
) -> ExperimentDTO:
    experiment_id = _next_experiment_id(run_dir)
    experiment_dir = run_dir / "experiments" / experiment_id
    candidate_dir = experiment_dir / "candidates"
    experiment_dir.mkdir(parents=True, exist_ok=False)
    candidate_dir.mkdir(parents=True, exist_ok=True)

    variants = [
        ExperimentVariantDTO(
            candidate_id=candidate.candidate_id,
            status="undecided",
            candidate=_persist_candidate(run_dir, candidate_dir, candidate),
        )
        for candidate in candidates
    ]
    experiment = ExperimentDTO(
        experiment_id=experiment_id,
        source_candidate_id=source_candidate_id,
        source_request=source_request,
        created_at=datetime.now(UTC).isoformat(),
        notes="",
        variants=variants,
    )
    _write_experiment(experiment_dir, experiment)
    return experiment


def list_experiments(run_dir: Path) -> list[ExperimentDTO]:
    experiments_dir = run_dir / "experiments"
    if not experiments_dir.exists():
        return []
    return [
        _read_experiment(path)
        for path in sorted(experiments_dir.glob("experiment-*/experiment.json"))
    ]


def patch_experiment(
    run_dir: Path,
    experiment_id: str,
    patch: ExperimentPatchDTO,
) -> ExperimentDTO:
    experiment_dir = _experiment_dir(run_dir, experiment_id)
    experiment = _read_experiment(experiment_dir / "experiment.json")
    status_updates = patch.variant_status
    variants = [
        variant.model_copy(
            update={"status": status_updates.get(variant.candidate_id, variant.status)}
        )
        for variant in experiment.variants
    ]
    updated = experiment.model_copy(
        update={
            "notes": experiment.notes if patch.notes is None else patch.notes,
            "variants": variants,
        }
    )
    _write_experiment(experiment_dir, updated)
    return updated


def _persist_candidate(
    run_dir: Path,
    candidate_dir: Path,
    candidate: CandidateVizDTO,
) -> CandidateVizDTO:
    core_candidate = candidate_from_dto(candidate)
    paths = write_candidate_exports(core_candidate, candidate_dir, stem=candidate.candidate_id)
    artifacts = {
        "musicxml": str(paths.musicxml.relative_to(run_dir)),
        "midi": str(paths.midi.relative_to(run_dir)),
    }
    try:
        register_candidate_artifacts(
            run_dir / "artifact_index.json",
            candidate.candidate_id,
            artifacts,
        )
    except ArtifactIndexError as exc:
        raise OutputError(
            "Candidate artifacts could not be registered.",
            code="candidate_artifact_registration_failed",
            details={"candidate_id": candidate.candidate_id, "error": str(exc)},
        ) from exc
    return materialize_candidate(
        replace(
            core_candidate,
            metadata={
                **core_candidate.metadata,
                "outputs": artifacts,
            },
        )
    )


def _next_experiment_id(run_dir: Path) -> str:
    experiments_dir = run_dir / "experiments"
    experiments_dir.mkdir(parents=True, exist_ok=True)
    existing = {path.name for path in experiments_dir.glob("experiment-*") if path.is_dir()}
    for index in range(1, 10000):
        experiment_id = f"experiment-{index:04d}"
        if experiment_id not in existing:
            return experiment_id
    raise OutputError(
        "Could not allocate an experiment id.",
        code="experiment_id_exhausted",
        details={"run_dir": str(run_dir)},
    )


def _experiment_dir(run_dir: Path, experiment_id: str) -> Path:
    if Path(experiment_id).name != experiment_id or not experiment_id.startswith("experiment-"):
        raise OutputError(
            "Experiment id is not valid.",
            code="invalid_experiment_id",
            details={"experiment_id": experiment_id},
        )
    experiment_dir = run_dir / "experiments" / experiment_id
    if not experiment_dir.is_dir():
        raise OutputError(
            "Experiment was not found.",
            code="experiment_not_found",
            details={"experiment_id": experiment_id},
        )
    return experiment_dir


def _read_experiment(path: Path) -> ExperimentDTO:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise OutputError(
            "Experiment could not be read.",
            code="experiment_read_failed",
            details={"path": str(path), "error": str(exc)},
        ) from exc
    except json.JSONDecodeError as exc:
        raise OutputError(
            "Experiment JSON is invalid.",
            code="experiment_json_invalid",
            details={"path": str(path), "error": str(exc)},
        ) from exc
    try:
        return ExperimentDTO.model_validate(payload)
    except ValidationError as exc:
        raise OutputError(
            "Experiment does not match the expected schema.",
            code="experiment_schema_invalid",
            details={"path": str(path), "errors": cast(Any, exc.errors(include_url=False))},
        ) from exc


def _write_experiment(experiment_dir: Path, experiment: ExperimentDTO) -> None:
    experiment_dir.mkdir(parents=True, exist_ok=True)
    (experiment_dir / "notes.md").write_text(experiment.notes, encoding="utf-8")
    (experiment_dir / "experiment.json").write_text(
        json.dumps(experiment.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
