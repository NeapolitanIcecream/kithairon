"""FastAPI application entry point for the Kithairon visualizer."""

import json
from collections.abc import Awaitable
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Protocol, TypeGuard, cast
from uuid import uuid4

import typer
from pydantic import BaseModel, Field
from rich.console import Console

from kithairon import __version__
from kithairon.config import KithaironConfig, build_config_overrides, deep_merge, load_config
from kithairon.errors import Diagnostic, KithaironError
from kithairon.pipeline import run_generation
from kithairon.visualization.artifact_index import (
    ArtifactIndexError,
    resolve_candidate_artifact,
    resolve_run_artifact,
    update_candidate_artifacts,
)
from kithairon.visualization.export_score import (
    ExternalScoreRenderError,
    RenderFormat,
    render_with_musescore,
)

console = Console()
ALLOWED_UPLOAD_SUFFIXES = {".mid", ".midi", ".musicxml", ".xml", ".mxl"}
DEFAULT_MAX_UPLOAD_BYTES = 10 * 1024 * 1024

cli = typer.Typer(
    name="canonize-web",
    help="Serve the Kithairon visualization API and frontend.",
    no_args_is_help=False,
)


def _option(*param_decls: str, **kwargs: Any) -> object:
    return typer.Option(*param_decls, **kwargs)  # pyright: ignore[reportUnknownMemberType]


OUTPUT_ROOT_OPTION: object = _option(
    "--output-root",
    file_okay=False,
    help="Directory where API-generated runs will be stored.",
)
HOST_OPTION: object = _option("--host", help="Host interface for the web server.")
PORT_OPTION: object = _option("--port", min=1, max=65535, help="Port for the web server.")
RELOAD_OPTION: object = _option("--reload/--no-reload", help="Enable Uvicorn reload mode.")
CORS_ORIGIN_OPTION: object = _option(
    "--cors-origin",
    help="Allowed CORS origin. May be passed multiple times.",
)
MUSESCORE_BIN_OPTION: object = _option(
    "--musescore-bin",
    exists=True,
    dir_okay=False,
    help="Optional MuseScore CLI binary used for PDF/SVG/PNG rendering.",
)
SERVE_FRONTEND_OPTION: object = _option(
    "--serve-frontend",
    exists=True,
    file_okay=False,
    help="Optional built frontend directory to serve in production mode.",
)
READ_ONLY_OPTION: object = _option(
    "--read-only/--no-read-only",
    help="Serve existing runs without accepting uploads or render mutations.",
)


@dataclass(frozen=True)
class ApiSettings:
    output_root: Path
    cors_origins: tuple[str, ...] = ()
    read_only: bool = False
    max_upload_bytes: int = DEFAULT_MAX_UPLOAD_BYTES
    musescore_bin: Path | None = None
    serve_frontend: Path | None = None


@dataclass(frozen=True)
class RunUploadRequest:
    filename: str
    content: bytes
    config_json: str | None
    top_k: int | None
    engine: str | None
    chord_policy: str | None
    part_policy: str | None
    part_index: int | None


class UploadFileLike(Protocol):
    filename: str | None

    def read(self) -> Awaitable[bytes]: ...


class RenderRequest(BaseModel):
    formats: list[RenderFormat] = Field(min_length=1)


class ApiError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int = 400,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.diagnostic = Diagnostic(
            code=code,
            message=message,
            details={} if details is None else details,
        )


def create_app(
    *,
    output_root: Path | None = None,
    cors_origins: tuple[str, ...] = (),
    read_only: bool = False,
    max_upload_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
    musescore_bin: Path | None = None,
    serve_frontend: Path | None = None,
) -> Any:
    """Create the visualization FastAPI application."""
    from fastapi import FastAPI

    app = FastAPI(title="Kithairon Visualization API", version=__version__)
    settings = ApiSettings(
        output_root=Path("runs") if output_root is None else output_root,
        cors_origins=cors_origins,
        read_only=read_only,
        max_upload_bytes=max_upload_bytes,
        musescore_bin=musescore_bin,
        serve_frontend=serve_frontend,
    )
    app.state.settings = settings
    _configure_cors(app, settings.cors_origins)
    _register_exception_handlers(app)
    _register_routes(app, settings)
    _mount_frontend(app, settings)
    return app


def _configure_cors(app: Any, cors_origins: tuple[str, ...]) -> None:
    if not cors_origins:
        return
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _register_exception_handlers(app: Any) -> None:
    app.add_exception_handler(ApiError, _api_error_handler)
    app.add_exception_handler(KithaironError, _project_error_handler)
    app.add_exception_handler(ArtifactIndexError, _artifact_error_handler)
    app.add_exception_handler(Exception, _unexpected_error_handler)


async def _api_error_handler(_request: object, exc: Exception) -> Any:
    from fastapi.responses import JSONResponse

    api_error = cast(ApiError, exc)
    return JSONResponse(
        status_code=api_error.status_code,
        content=api_error.diagnostic.to_dict(),
    )


async def _project_error_handler(_request: object, exc: Exception) -> Any:
    from fastapi.responses import JSONResponse

    project_error = cast(KithaironError, exc)
    return JSONResponse(status_code=400, content=project_error.to_diagnostic())


async def _artifact_error_handler(_request: object, exc: Exception) -> Any:
    from fastapi.responses import JSONResponse

    artifact_error = cast(ArtifactIndexError, exc)
    return JSONResponse(
        status_code=400,
        content=Diagnostic(
            code="artifact_index_error",
            message=str(artifact_error),
        ).to_dict(),
    )


async def _unexpected_error_handler(_request: object, exc: Exception) -> Any:
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=500,
        content=Diagnostic(
            code="internal_error",
            message="An unexpected internal error occurred.",
            details={"error_type": type(exc).__name__},
        ).to_dict(),
    )


def _register_routes(app: Any, settings: ApiSettings) -> None:
    app.add_api_route("/api/health", _health, methods=["GET"])
    app.add_api_route("/api/runs", _create_run_endpoint(settings), methods=["POST"])
    app.add_api_route("/api/runs/{run_id}", _get_run_endpoint(settings), methods=["GET"])
    app.add_api_route(
        "/api/runs/{run_id}/visualization",
        _get_run_visualization_endpoint(settings),
        methods=["GET"],
    )
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


def _health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "kithairon-visualization",
        "version": __version__,
    }


def _create_run_endpoint(settings: ApiSettings) -> Any:
    from fastapi import Request

    async def create_run(request: Request) -> dict[str, object]:
        return await _create_run_from_request(request, settings)

    return create_run


def _get_run_endpoint(settings: ApiSettings) -> Any:
    def get_run(run_id: str) -> dict[str, object]:
        return _run_visualization(settings, run_id)

    return get_run


def _get_run_visualization_endpoint(settings: ApiSettings) -> Any:
    def get_run_visualization(run_id: str) -> dict[str, object]:
        return _run_visualization(settings, run_id)

    return get_run_visualization


def _get_run_artifact_endpoint(settings: ApiSettings) -> Any:
    def get_run_artifact(run_id: str, kind: str) -> Any:
        return _run_artifact_response(settings, run_id, kind)

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


def _mount_frontend(app: Any, settings: ApiSettings) -> None:
    if settings.serve_frontend is None:
        return
    from fastapi.staticfiles import StaticFiles

    app.mount(
        "/",
        StaticFiles(directory=settings.serve_frontend, html=True),
        name="frontend",
    )


@cli.callback(invoke_without_command=True)
def serve(
    output_root: Annotated[Path, OUTPUT_ROOT_OPTION] = Path("runs"),
    host: Annotated[str, HOST_OPTION] = "127.0.0.1",
    port: Annotated[int, PORT_OPTION] = 8000,
    reload: Annotated[bool, RELOAD_OPTION] = False,
    cors_origin: Annotated[list[str] | None, CORS_ORIGIN_OPTION] = None,
    musescore_bin: Annotated[Path | None, MUSESCORE_BIN_OPTION] = None,
    serve_frontend: Annotated[Path | None, SERVE_FRONTEND_OPTION] = None,
    read_only: Annotated[bool, READ_ONLY_OPTION] = False,
) -> None:
    """Serve the visualization API."""
    import uvicorn

    output_root.mkdir(parents=True, exist_ok=True)
    app_instance = create_app(
        output_root=output_root,
        cors_origins=tuple(cors_origin or ()),
        read_only=read_only,
        musescore_bin=musescore_bin,
        serve_frontend=serve_frontend,
    )
    console.print(f"Serving Kithairon visualization API on http://{host}:{port}")
    uvicorn.run(
        app_instance,
        host=host,
        port=port,
        reload=reload,
    )


def main() -> None:
    """Run the canonize-web command line application."""
    cli()


async def _create_run_from_request(request: Any, settings: ApiSettings) -> dict[str, object]:
    upload = await _read_upload_request(request, settings)
    input_path, output_dir = _store_upload(settings, upload)
    request_config = _request_config(
        config_json=upload.config_json,
        top_k=upload.top_k,
        engine=upload.engine,
        chord_policy=upload.chord_policy,
        part_policy=upload.part_policy,
        part_index=upload.part_index,
    )
    generation = run_generation(input_path, output_dir, request_config, overwrite_output=True)
    return _read_json_object(generation.visualization_path)


async def _read_upload_request(request: Any, settings: ApiSettings) -> RunUploadRequest:
    if settings.read_only:
        raise ApiError(
            "This server is running in read-only mode.",
            code="read_only_mode",
            status_code=403,
        )
    form = await request.form()
    upload = _form_upload(form)
    content = await upload.read()
    _validate_upload_size(content, settings)
    return RunUploadRequest(
        filename=_safe_upload_filename(upload.filename),
        content=content,
        config_json=_form_text(form, "config"),
        top_k=_form_int(form, "top_k"),
        engine=_form_text(form, "engine"),
        chord_policy=_form_text(form, "chord_policy"),
        part_policy=_form_text(form, "part_policy"),
        part_index=_form_int(form, "part_index"),
    )


def _form_upload(form: Any) -> UploadFileLike:
    value = form.get("file")
    if not _is_upload_file_like(value):
        raise ApiError(
            "Upload request must include a score file.",
            code="upload_file_missing",
        )
    return value


def _is_upload_file_like(value: object) -> TypeGuard[UploadFileLike]:
    return hasattr(value, "filename") and callable(getattr(value, "read", None))


def _form_text(form: Any, field_name: str) -> str | None:
    value = form.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ApiError(
            "Upload form field must be text.",
            code="upload_field_not_text",
            details={"field": field_name},
        )
    return value


def _form_int(form: Any, field_name: str) -> int | None:
    value = _form_text(form, field_name)
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ApiError(
            "Upload form field must be an integer.",
            code="upload_field_not_integer",
            details={"field": field_name, "value": value},
        ) from exc


def _validate_upload_size(content: bytes, settings: ApiSettings) -> None:
    if len(content) <= settings.max_upload_bytes:
        return
    raise ApiError(
        "Uploaded file exceeds the maximum allowed size.",
        code="upload_too_large",
        status_code=413,
        details={"max_bytes": settings.max_upload_bytes, "actual_bytes": len(content)},
    )


def _store_upload(settings: ApiSettings, upload: RunUploadRequest) -> tuple[Path, Path]:
    run_id = uuid4().hex
    upload_dir = settings.output_root / "_uploads" / run_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    input_path = upload_dir / upload.filename
    input_path.write_bytes(upload.content)
    return input_path, settings.output_root / run_id


def _safe_upload_filename(filename: str | None) -> str:
    safe_name = Path(filename or "").name
    suffix = Path(safe_name).suffix.lower()
    if not safe_name or suffix not in ALLOWED_UPLOAD_SUFFIXES:
        raise ApiError(
            "Uploaded file type is not supported.",
            code="unsupported_upload_format",
            details={
                "filename": filename or "",
                "allowed_suffixes": sorted(ALLOWED_UPLOAD_SUFFIXES),
            },
        )
    return safe_name


def _request_config(
    *,
    config_json: str | None,
    top_k: int | None,
    engine: str | None,
    chord_policy: str | None,
    part_policy: str | None,
    part_index: int | None,
) -> KithaironConfig:
    config_data = _config_payload(config_json)
    overrides = build_config_overrides(
        chord_policy=chord_policy,
        part_policy=part_policy,
        part_index=part_index,
        engine=engine,
        top_k=top_k,
    )
    return load_config(None, deep_merge(config_data, overrides))


def _config_payload(config_json: str | None) -> dict[str, object]:
    if config_json is None or not config_json.strip():
        return {}
    try:
        payload = json.loads(config_json)
    except json.JSONDecodeError as exc:
        raise ApiError(
            "Config form field must be valid JSON.",
            code="config_invalid_json",
            details={"error": str(exc)},
        ) from exc
    if not isinstance(payload, dict):
        raise ApiError(
            "Config form field must be a JSON object.",
            code="config_not_object",
        )
    mapped = cast(dict[object, object], payload)
    return {str(key): value for key, value in mapped.items()}


def _read_json_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ApiError(
            "Generated visualization payload is not a JSON object.",
            code="visualization_payload_invalid",
        )
    mapped = cast(dict[object, object], payload)
    return {str(key): value for key, value in mapped.items()}


def _run_artifact_response(settings: ApiSettings, run_id: str, kind: str) -> Any:
    index_path = _artifact_index_path(settings, run_id)
    return _download_response(resolve_run_artifact(index_path, kind))


def _candidate_payload(settings: ApiSettings, run_id: str, candidate_id: str) -> dict[str, object]:
    candidates = _visualization_candidates(_run_visualization(settings, run_id))
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
    index_path = _artifact_index_path(settings, run_id)
    artifact_path = resolve_candidate_artifact(index_path, candidate_id, kind)
    return _download_response(artifact_path)


def _render_candidate_response(
    settings: ApiSettings,
    run_id: str,
    candidate_id: str,
    request: RenderRequest,
) -> dict[str, object]:
    if settings.musescore_bin is None:
        raise ApiError(
            "MuseScore CLI is not configured. Set MUSESCORE_BIN or --musescore-bin.",
            code="external_renderer_unavailable",
            status_code=503,
        )
    index_path = _artifact_index_path(settings, run_id)
    rendered = _render_candidate_formats(settings, run_id, candidate_id, request.formats)
    update_candidate_artifacts(index_path, candidate_id, rendered)
    return {"candidate_id": candidate_id, "artifacts": rendered}


def _render_candidate_formats(
    settings: ApiSettings,
    run_id: str,
    candidate_id: str,
    formats: list[RenderFormat],
) -> dict[str, str]:
    index_path = _artifact_index_path(settings, run_id)
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
    return str(output_path.relative_to(_run_dir(settings, run_id)))


def _run_visualization(settings: ApiSettings, run_id: str) -> dict[str, object]:
    return _read_json_object(_run_dir(settings, run_id) / "visualization.json")


def _artifact_index_path(settings: ApiSettings, run_id: str) -> Path:
    return _run_dir(settings, run_id) / "artifact_index.json"


def _run_dir(settings: ApiSettings, run_id: str) -> Path:
    if Path(run_id).name != run_id or run_id in {"", ".", ".."}:
        raise ApiError(
            "Run id is not valid.",
            code="invalid_run_id",
            status_code=400,
            details={"run_id": run_id},
        )
    return settings.output_root / run_id


def _download_response(path: Path) -> Any:
    from fastapi.responses import FileResponse

    if not path.exists() or not path.is_file():
        raise ApiError(
            "Artifact file was not found.",
            code="artifact_not_found",
            status_code=404,
            details={"path": str(path)},
        )
    return FileResponse(path, filename=path.name)


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
    return _run_dir(settings, run_id) / "renders" / candidate_id / f"{candidate_id}.{fmt}"
