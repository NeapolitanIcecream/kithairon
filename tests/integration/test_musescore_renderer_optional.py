from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from kithairon.api.app import create_app


def test_render_endpoint_reports_missing_musescore_configuration(tmp_path: Path) -> None:
    client = TestClient(create_app(output_root=tmp_path))
    run = _create_run(client)
    candidate_id = _first_candidate_id(run)

    response = client.post(
        f"/api/runs/{run['run_id']}/candidates/{candidate_id}/render",
        json={"formats": ["pdf"]},
    )

    assert response.status_code == 503
    assert response.json()["code"] == "external_renderer_unavailable"


def test_render_endpoint_generates_pdf_when_musescore_is_available(tmp_path: Path) -> None:
    musescore = shutil.which("mscore") or shutil.which("musescore")
    if musescore is None:
        pytest.skip("MuseScore CLI is not installed")

    client = TestClient(create_app(output_root=tmp_path, musescore_bin=Path(musescore)))
    run = _create_run(client)
    candidate_id = _first_candidate_id(run)

    response = client.post(
        f"/api/runs/{run['run_id']}/candidates/{candidate_id}/render",
        json={"formats": ["pdf"]},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    rendered_pdf = tmp_path / cast(str, run["run_id"]) / payload["artifacts"]["pdf"]
    assert rendered_pdf.exists()


def _create_run(client: TestClient) -> dict[str, Any]:
    with Path("examples/melodies/scale_c_major.musicxml").open("rb") as handle:
        response = client.post(
            "/api/runs",
            files={"file": ("scale_c_major.musicxml", handle, "application/xml")},
            data={"engine": "strict", "top_k": "1"},
        )
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def _first_candidate_id(run: dict[str, Any]) -> str:
    candidates = cast(list[dict[str, Any]], run["candidates"])
    return cast(str, candidates[0]["candidate_id"])
