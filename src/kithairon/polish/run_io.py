"""Run-directory loading helpers for local phrase polish."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from pydantic import ValidationError

from kithairon.config import load_config
from kithairon.errors import PolishError
from kithairon.polish.apply import polish_candidate_dto
from kithairon.polish.models import PolishRequest, PolishResultDTO
from kithairon.visualization.models import CandidateVizDTO, RunSummaryDTO


def polish_run_candidate(
    run_dir: Path,
    candidate_id: str,
    request: PolishRequest,
) -> PolishResultDTO:
    run = load_run_summary(run_dir)
    candidate = _candidate_by_id(run, candidate_id)
    config_path = run_dir / "resolved_config.toml"
    config = load_config(config_path if config_path.exists() else None)
    return polish_candidate_dto(
        candidate,
        request,
        score_profile=config.scoring.profile,
        quality=config.quality,
    )


def load_run_summary(run_dir: Path) -> RunSummaryDTO:
    path = run_dir / "visualization.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise PolishError(
            "Run visualization could not be read.",
            code="polish_visualization_unavailable",
            details={"path": str(path), "error": str(exc)},
        ) from exc
    except json.JSONDecodeError as exc:
        raise PolishError(
            "Run visualization is not valid JSON.",
            code="polish_visualization_invalid_json",
            details={"path": str(path), "error": str(exc)},
        ) from exc

    try:
        return RunSummaryDTO.model_validate(payload)
    except ValidationError as exc:
        raise PolishError(
            "Run visualization does not match the expected schema.",
            code="polish_visualization_invalid",
            details={"path": str(path), "errors": cast(object, exc.errors(include_url=False))},
        ) from exc


def _candidate_by_id(run: RunSummaryDTO, candidate_id: str) -> CandidateVizDTO:
    for candidate in run.candidates:
        if candidate.candidate_id == candidate_id:
            return candidate
    raise PolishError(
        "Candidate was not found in this run.",
        code="polish_candidate_not_found",
        details={"run_id": run.run_id, "candidate_id": candidate_id},
    )
