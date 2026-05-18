from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient

from kithairon.api.app import create_app


def test_health_endpoint_returns_service_status(tmp_path: Path) -> None:
    client = TestClient(create_app(output_root=tmp_path))

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_run_upload_generates_visualization_summary(tmp_path: Path) -> None:
    client = TestClient(create_app(output_root=tmp_path))

    with Path("examples/melodies/scale_c_major.musicxml").open("rb") as handle:
        response = client.post(
            "/api/runs",
            files={"file": ("scale_c_major.musicxml", handle, "application/xml")},
            data={"engine": "strict", "top_k": "1"},
        )

    assert response.status_code == 200, response.text
    payload = cast(dict[str, Any], response.json())
    run_id = cast(str, payload["run_id"])
    assert payload["input_name"] == "scale_c_major.musicxml"
    assert len(cast(list[object], payload["candidates"])) == 1
    assert (tmp_path / run_id / "visualization.json").exists()
    assert (tmp_path / run_id / "artifact_index.json").exists()


def test_run_upload_rejects_unsupported_suffix(tmp_path: Path) -> None:
    client = TestClient(create_app(output_root=tmp_path))

    response = client.post(
        "/api/runs",
        files={"file": ("melody.txt", b"not a score", "text/plain")},
        data={"engine": "strict"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "unsupported_upload_format"


def test_run_upload_honors_read_only_mode(tmp_path: Path) -> None:
    client = TestClient(create_app(output_root=tmp_path, read_only=True))

    response = client.post(
        "/api/runs",
        files={"file": ("scale.musicxml", b"<score-partwise />", "application/xml")},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "read_only_mode"


def test_cors_allows_configured_origin(tmp_path: Path) -> None:
    client = TestClient(
        create_app(output_root=tmp_path, cors_origins=("http://localhost:5173",))
    )

    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
