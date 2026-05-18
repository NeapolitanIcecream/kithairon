"""FastAPI application entry point for the Kithairon visualizer."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from kithairon import __version__

console = Console()

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


def create_app() -> Any:
    """Create the visualization FastAPI application."""
    from fastapi import FastAPI

    app = FastAPI(title="Kithairon Visualization API", version=__version__)

    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "kithairon-visualization",
            "version": __version__,
        }

    app.add_api_route("/api/health", health, methods=["GET"])
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
    _ = (output_root, cors_origin, musescore_bin, serve_frontend, read_only)
    import uvicorn

    console.print(f"Serving Kithairon visualization API on http://{host}:{port}")
    uvicorn.run(
        "kithairon.api.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
    )


def main() -> None:
    """Run the canonize-web command line application."""
    cli()
