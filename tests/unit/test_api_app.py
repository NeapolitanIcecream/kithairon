from __future__ import annotations

from pathlib import Path

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from kithairon.api.app import cli, create_app


def test_canonize_web_help_documents_server_options() -> None:
    result = CliRunner().invoke(cli, ["--help"], terminal_width=160, color=False)

    assert result.exit_code == 0, result.stdout
    assert "--output-root" in result.stdout
    assert "--serve-frontend" in result.stdout
    assert "--read-only" in result.stdout


def test_create_app_exposes_health_endpoint() -> None:
    app = create_app()

    routes = {route.path for route in app.routes if isinstance(route, APIRoute)}

    assert "/api/health" in routes


def test_create_app_serves_built_frontend_without_hiding_api(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    assets = dist / "assets"
    assets.mkdir(parents=True)
    (dist / "index.html").write_text("<main>Kithairon app</main>", encoding="utf-8")
    (assets / "app.js").write_text("console.log('app')", encoding="utf-8")

    client = TestClient(create_app(serve_frontend=dist))

    assert "Kithairon app" in client.get("/").text
    assert "console.log" in client.get("/assets/app.js").text
    assert client.get("/api/health").json()["status"] == "ok"
