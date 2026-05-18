"""FastAPI application entry point for the Kithairon visualizer."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, cast
from uuid import uuid4

import typer
from rich.console import Console

from kithairon import __version__
from kithairon.config import KithaironConfig, build_config_overrides, deep_merge, load_config
from kithairon.errors import Diagnostic, KithaironError
from kithairon.pipeline import run_generation
from kithairon.visualization.artifact_index import (
    ArtifactIndexError,
    resolve_candidate_artifact,
    resolve_run_artifact,
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
) -> Any:
    """Create the visualization FastAPI application."""
    from fastapi import FastAPI, File, Form, Request, UploadFile
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse, JSONResponse

    app = FastAPI(title="Kithairon Visualization API", version=__version__)
    settings = ApiSettings(
        output_root=Path("runs") if output_root is None else output_root,
        cors_origins=cors_origins,
        read_only=read_only,
        max_upload_bytes=max_upload_bytes,
    )
    app.state.settings = settings

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    async def api_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        api_error = cast(ApiError, exc)
        return JSONResponse(
            status_code=api_error.status_code,
            content=api_error.diagnostic.to_dict(),
        )

    async def project_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        project_error = cast(KithaironError, exc)
        return JSONResponse(status_code=400, content=project_error.to_diagnostic())

    async def artifact_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        artifact_error = cast(ArtifactIndexError, exc)
        return JSONResponse(
            status_code=400,
            content=Diagnostic(
                code="artifact_index_error",
                message=str(artifact_error),
            ).to_dict(),
        )

    async def unexpected_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=Diagnostic(
                code="internal_error",
                message="An unexpected internal error occurred.",
                details={"error_type": type(exc).__name__},
            ).to_dict(),
        )

    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(KithaironError, project_error_handler)
    app.add_exception_handler(ArtifactIndexError, artifact_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)

    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "kithairon-visualization",
            "version": __version__,
        }

    app.add_api_route("/api/health", health, methods=["GET"])

    file_field = File(...)
    config_field = Form(None)
    top_k_field = Form(None)
    engine_field = Form(None)
    chord_policy_field = Form(None)
    part_policy_field = Form(None)
    part_index_field = Form(None)

    async def create_run(
        file: UploadFile = file_field,
        config: str | None = config_field,
        top_k: int | None = top_k_field,
        engine: str | None = engine_field,
        chord_policy: str | None = chord_policy_field,
        part_policy: str | None = part_policy_field,
        part_index: int | None = part_index_field,
    ) -> dict[str, object]:
        if settings.read_only:
            raise ApiError(
                "This server is running in read-only mode.",
                code="read_only_mode",
                status_code=403,
            )

        filename = _safe_upload_filename(file.filename)
        content = await file.read()
        if len(content) > settings.max_upload_bytes:
            raise ApiError(
                "Uploaded file exceeds the maximum allowed size.",
                code="upload_too_large",
                status_code=413,
                details={"max_bytes": settings.max_upload_bytes, "actual_bytes": len(content)},
            )

        run_id = uuid4().hex
        upload_dir = settings.output_root / "_uploads" / run_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        input_path = upload_dir / filename
        input_path.write_bytes(content)

        output_dir = settings.output_root / run_id
        request_config = _request_config(
            config_json=config,
            top_k=top_k,
            engine=engine,
            chord_policy=chord_policy,
            part_policy=part_policy,
            part_index=part_index,
        )
        generation = run_generation(input_path, output_dir, request_config, overwrite_output=True)
        return _read_json_object(generation.visualization_path)

    app.add_api_route("/api/runs", create_run, methods=["POST"])

    def get_run(run_id: str) -> dict[str, object]:
        return _run_visualization(settings, run_id)

    def get_run_visualization(run_id: str) -> dict[str, object]:
        return _run_visualization(settings, run_id)

    def get_run_artifact(run_id: str, kind: str) -> FileResponse:
        index_path = _artifact_index_path(settings, run_id)
        artifact_path = resolve_run_artifact(index_path, kind)
        return _download_response(artifact_path)

    def get_candidate(run_id: str, candidate_id: str) -> dict[str, object]:
        visualization = _run_visualization(settings, run_id)
        candidates = visualization.get("candidates")
        if not isinstance(candidates, list):
            raise ApiError(
                "Visualization payload does not contain candidates.",
                code="visualization_candidates_invalid",
                status_code=500,
            )
        for candidate in cast(list[object], candidates):
            if not isinstance(candidate, dict):
                continue
            mapped = cast(dict[object, object], candidate)
            if mapped.get("candidate_id") == candidate_id:
                return {str(key): value for key, value in mapped.items()}
        raise ApiError(
            "Candidate was not found in this run.",
            code="candidate_not_found",
            status_code=404,
            details={"run_id": run_id, "candidate_id": candidate_id},
        )

    def get_candidate_artifact(run_id: str, candidate_id: str, kind: str) -> FileResponse:
        index_path = _artifact_index_path(settings, run_id)
        artifact_path = resolve_candidate_artifact(index_path, candidate_id, kind)
        return _download_response(artifact_path)

    def get_candidate_musicxml(run_id: str, candidate_id: str) -> FileResponse:
        return get_candidate_artifact(run_id, candidate_id, "musicxml")

    def get_candidate_midi(run_id: str, candidate_id: str) -> FileResponse:
        return get_candidate_artifact(run_id, candidate_id, "midi")

    app.add_api_route("/api/runs/{run_id}", get_run, methods=["GET"])
    app.add_api_route("/api/runs/{run_id}/visualization", get_run_visualization, methods=["GET"])
    app.add_api_route("/api/runs/{run_id}/artifact/{kind}", get_run_artifact, methods=["GET"])
    app.add_api_route(
        "/api/runs/{run_id}/candidates/{candidate_id}",
        get_candidate,
        methods=["GET"],
    )
    app.add_api_route(
        "/api/runs/{run_id}/candidates/{candidate_id}/musicxml",
        get_candidate_musicxml,
        methods=["GET"],
    )
    app.add_api_route(
        "/api/runs/{run_id}/candidates/{candidate_id}/midi",
        get_candidate_midi,
        methods=["GET"],
    )
    app.add_api_route(
        "/api/runs/{run_id}/candidates/{candidate_id}/artifact/{kind}",
        get_candidate_artifact,
        methods=["GET"],
    )
    return app


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
    _ = (musescore_bin, serve_frontend)
    import uvicorn

    output_root.mkdir(parents=True, exist_ok=True)
    app_instance = create_app(
        output_root=output_root,
        cors_origins=tuple(cors_origin or ()),
        read_only=read_only,
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
