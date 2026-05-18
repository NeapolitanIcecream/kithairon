from __future__ import annotations

from fastapi.routing import APIRoute
from typer.testing import CliRunner

from kithairon.api.app import cli, create_app


def test_canonize_web_help_documents_server_options() -> None:
    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0, result.stdout
    assert "--output-root" in result.stdout
    assert "--serve-frontend" in result.stdout
    assert "--read-only" in result.stdout


def test_create_app_exposes_health_endpoint() -> None:
    app = create_app()

    routes = {route.path for route in app.routes if isinstance(route, APIRoute)}

    assert "/api/health" in routes
