"""Artifact download and rendering routes for the visualization API."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from kithairon.api.app import (
    ApiError,
    ApiSettings,
    RenderRequest,
    artifact_index_path,
    download_response,
    read_json_object,
    run_dir,
)
from kithairon.visualization.artifact_index import (
    resolve_candidate_artifact,
    resolve_run_artifact,
    update_candidate_artifacts,
)
from kithairon.visualization.export_score import (
    ExternalScoreRenderError,
    RenderFormat,
    render_with_musescore,
)


def register_artifact_routes(app: Any, settings: ApiSettings) -> None:
    app.add_api_route(
        "/api/runs/{run_id}/artifact/{kind}",
        _get_run_artifact_endpoint(settings),
        methods=["GET"],
    )
    app.add_api_route(
        "/api/runs/{run_id}/candidates/{candidate_id}",
        _get_candidate_endpoint(settings),
        methods=["GET"],
    )
    app.add_api_route(
        "/api/runs/{run_id}/candidates/{candidate_id}/musicxml",
        _get_candidate_musicxml_endpoint(settings),
        methods=["GET"],
    )
    app.add_api_route(
        "/api/runs/{run_id}/candidates/{candidate_id}/midi",
        _get_candidate_midi_endpoint(settings),
        methods=["GET"],
    )
    app.add_api_route(
        "/api/runs/{run_id}/candidates/{candidate_id}/artifact/{kind}",
        _get_candidate_artifact_endpoint(settings),
        methods=["GET"],
    )
    app.add_api_route(
        "/api/runs/{run_id}/candidates/{candidate_id}/render",
        _render_candidate_endpoint(settings),
        methods=["POST"],
    )


def _get_run_artifact_endpoint(settings: ApiSettings) -> Any:
    def get_run_artifact(run_id: str, kind: str) -> Any:
        index_path = artifact_index_path(settings, run_id)
        return download_response(resolve_run_artifact(index_path, kind))

    return get_run_artifact


def _get_candidate_endpoint(settings: ApiSettings) -> Any:
    def get_candidate(run_id: str, candidate_id: str) -> dict[str, object]:
        return _candidate_payload(settings, run_id, candidate_id)

    return get_candidate


def _get_candidate_musicxml_endpoint(settings: ApiSettings) -> Any:
    def get_candidate_musicxml(run_id: str, candidate_id: str) -> Any:
        return _candidate_artifact_response(settings, run_id, candidate_id, "musicxml")

    return get_candidate_musicxml


def _get_candidate_midi_endpoint(settings: ApiSettings) -> Any:
    def get_candidate_midi(run_id: str, candidate_id: str) -> Any:
        return _candidate_artifact_response(settings, run_id, candidate_id, "midi")

    return get_candidate_midi


def _get_candidate_artifact_endpoint(settings: ApiSettings) -> Any:
    def get_candidate_artifact(run_id: str, candidate_id: str, kind: str) -> Any:
        return _candidate_artifact_response(settings, run_id, candidate_id, kind)

    return get_candidate_artifact


def _render_candidate_endpoint(settings: ApiSettings) -> Any:
    def render_candidate(
        run_id: str,
        candidate_id: str,
        request: RenderRequest,
    ) -> dict[str, object]:
        return _render_candidate_response(settings, run_id, candidate_id, request)

    return render_candidate


def _candidate_payload(settings: ApiSettings, run_id: str, candidate_id: str) -> dict[str, object]:
    candidates = _visualization_candidates(
        read_json_object(run_dir(settings, run_id) / "visualization.json")
    )
    for candidate in candidates:
        if candidate.get("candidate_id") == candidate_id:
            return {str(key): value for key, value in candidate.items()}
    raise ApiError(
        "Candidate was not found in this run.",
        code="candidate_not_found",
        status_code=404,
        details={"run_id": run_id, "candidate_id": candidate_id},
    )


def _visualization_candidates(visualization: dict[str, object]) -> list[dict[object, object]]:
    candidates = visualization.get("candidates")
    if not isinstance(candidates, list):
        raise ApiError(
            "Visualization payload does not contain candidates.",
            code="visualization_candidates_invalid",
            status_code=500,
        )
    mapped_candidates: list[dict[object, object]] = []
    for candidate in cast(list[object], candidates):
        if isinstance(candidate, dict):
            mapped_candidates.append(cast(dict[object, object], candidate))
    return mapped_candidates


def _candidate_artifact_response(
    settings: ApiSettings,
    run_id: str,
    candidate_id: str,
    kind: str,
) -> Any:
    index_path = artifact_index_path(settings, run_id)
    artifact_path = resolve_candidate_artifact(index_path, candidate_id, kind)
    return download_response(artifact_path)


def _render_candidate_response(
    settings: ApiSettings,
    run_id: str,
    candidate_id: str,
    request: RenderRequest,
) -> dict[str, object]:
    if settings.read_only:
        raise ApiError(
            "This server is running in read-only mode.",
            code="read_only_mode",
            status_code=403,
        )
    if settings.musescore_bin is None:
        raise ApiError(
            "MuseScore CLI is not configured. Set MUSESCORE_BIN or --musescore-bin.",
            code="external_renderer_unavailable",
            status_code=503,
        )
    index_path = artifact_index_path(settings, run_id)
    rendered = _render_candidate_formats(settings, run_id, candidate_id, request.formats)
    update_candidate_artifacts(index_path, candidate_id, rendered)
    return {"candidate_id": candidate_id, "artifacts": rendered}


def _render_candidate_formats(
    settings: ApiSettings,
    run_id: str,
    candidate_id: str,
    formats: list[RenderFormat],
) -> dict[str, str]:
    index_path = artifact_index_path(settings, run_id)
    musicxml_path = resolve_candidate_artifact(index_path, candidate_id, "musicxml")
    return {
        fmt: _render_candidate_format(settings, run_id, candidate_id, fmt, musicxml_path)
        for fmt in formats
    }


def _render_candidate_format(
    settings: ApiSettings,
    run_id: str,
    candidate_id: str,
    fmt: RenderFormat,
    musicxml_path: Path,
) -> str:
    output_path = _render_output_path(settings, run_id, candidate_id, fmt)
    try:
        render_with_musescore(
            musicxml_path,
            output_path,
            fmt,
            cast(Path, settings.musescore_bin),
        )
    except ExternalScoreRenderError as exc:
        raise ApiError(
            str(exc),
            code="external_renderer_failed",
            status_code=502,
        ) from exc
    return str(output_path.relative_to(run_dir(settings, run_id)))


def _render_output_path(
    settings: ApiSettings,
    run_id: str,
    candidate_id: str,
    fmt: RenderFormat,
) -> Path:
    safe_candidate_id = Path(candidate_id).name
    if safe_candidate_id != candidate_id or candidate_id in {"", ".", ".."}:
        raise ApiError(
            "Candidate id is not valid.",
            code="invalid_candidate_id",
            status_code=400,
            details={"candidate_id": candidate_id},
        )
    return run_dir(settings, run_id) / "renders" / candidate_id / f"{candidate_id}.{fmt}"
