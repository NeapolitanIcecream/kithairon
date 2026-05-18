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
    from fastapi.responses import JSONResponse

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
