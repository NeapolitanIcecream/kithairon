"""Unified run-local candidate catalog."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import ValidationError

from kithairon.errors import OutputError
from kithairon.experiments.store import list_experiments
from kithairon.visualization.models import CandidateVizDTO, RunSummaryDTO

type CandidateSourceKind = Literal["run", "experiment"]


@dataclass(frozen=True)
class CandidateCatalogEntry:
    candidate: CandidateVizDTO
    source_kind: CandidateSourceKind
    source_experiment_id: str | None
    parent_candidate_id: str | None


@dataclass(frozen=True)
class CandidateCatalog:
    run_id: str
    entries: tuple[CandidateCatalogEntry, ...]

    @property
    def candidates(self) -> tuple[CandidateVizDTO, ...]:
        return tuple(entry.candidate for entry in self.entries)

    def get(self, candidate_id: str) -> CandidateCatalogEntry:
        for entry in self.entries:
            if entry.candidate.candidate_id == candidate_id:
                return entry
        raise OutputError(
            "Candidate was not found in this run.",
            code="candidate_not_found",
            details={"run_id": self.run_id, "candidate_id": candidate_id},
        )


def load_candidate_catalog(run_dir: Path) -> CandidateCatalog:
    """Load base run candidates and experiment variants through one read path."""
    run = _read_run_summary(run_dir)
    entries: list[CandidateCatalogEntry] = [
        _entry(
            candidate,
            source_kind="run",
            source_experiment_id=None,
            parent_candidate_id=_string_or_none(candidate.metadata.get("parent_candidate_id")),
        )
        for candidate in run.candidates
    ]
    for experiment in list_experiments(run_dir):
        for variant in experiment.variants:
            parent_candidate_id = _string_or_none(
                variant.candidate.metadata.get("parent_candidate_id")
            )
            entries.append(
                _entry(
                    variant.candidate,
                    source_kind="experiment",
                    source_experiment_id=experiment.experiment_id,
                    parent_candidate_id=parent_candidate_id or experiment.source_candidate_id,
                )
            )
    return CandidateCatalog(run_id=run.run_id, entries=tuple(entries))


def _entry(
    candidate: CandidateVizDTO,
    *,
    source_kind: CandidateSourceKind,
    source_experiment_id: str | None,
    parent_candidate_id: str | None,
) -> CandidateCatalogEntry:
    candidate_with_provenance = candidate.model_copy(
        update={
            "metadata": {
                **candidate.metadata,
                "source_kind": source_kind,
                "source_experiment_id": source_experiment_id,
                "parent_candidate_id": parent_candidate_id,
            }
        }
    )
    return CandidateCatalogEntry(
        candidate=candidate_with_provenance,
        source_kind=source_kind,
        source_experiment_id=source_experiment_id,
        parent_candidate_id=parent_candidate_id,
    )


def _read_run_summary(run_dir: Path) -> RunSummaryDTO:
    path = run_dir / "visualization.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise OutputError(
            "Run visualization could not be read.",
            code="candidate_catalog_visualization_unavailable",
            details={"path": str(path), "error": str(exc)},
        ) from exc
    except json.JSONDecodeError as exc:
        raise OutputError(
            "Run visualization is not valid JSON.",
            code="candidate_catalog_visualization_invalid_json",
            details={"path": str(path), "error": str(exc)},
        ) from exc
    try:
        return RunSummaryDTO.model_validate(payload)
    except ValidationError as exc:
        raise OutputError(
            "Run visualization does not match the expected schema.",
            code="candidate_catalog_visualization_invalid",
            details={"path": str(path), "errors": cast(Any, exc.errors(include_url=False))},
        ) from exc


def _string_or_none(value: object) -> str | None:
    return value if isinstance(value, str) else None
