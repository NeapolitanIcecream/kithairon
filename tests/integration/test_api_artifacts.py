from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient

from kithairon.api.app import create_app


def test_artifact_endpoints_serve_generated_run_files(tmp_path: Path) -> None:
    client = TestClient(create_app(output_root=tmp_path))
    run = _create_run(client)
    candidate_id = _first_candidate_id(run)

    visualization = client.get(f"/api/runs/{run['run_id']}/visualization")
    report = client.get(f"/api/runs/{run['run_id']}/artifact/report")
    musicxml = client.get(f"/api/runs/{run['run_id']}/candidates/{candidate_id}/musicxml")
    midi = client.get(f"/api/runs/{run['run_id']}/candidates/{candidate_id}/midi")
    candidate = client.get(f"/api/runs/{run['run_id']}/candidates/{candidate_id}")

    assert visualization.status_code == 200
    assert visualization.json()["run_id"] == run["run_id"]
    assert report.status_code == 200
    assert "Top candidates" in report.text
    assert musicxml.status_code == 200
    assert b"score-partwise" in musicxml.content
    assert midi.status_code == 200
    assert midi.content[:4] == b"MThd"
    assert candidate.status_code == 200
    assert candidate.json()["candidate_id"] == candidate_id


def test_artifact_endpoint_rejects_index_path_traversal(tmp_path: Path) -> None:
    run_dir = tmp_path / "unsafe"
    run_dir.mkdir()
    (run_dir / "visualization.json").write_text(
        json.dumps({"run_id": "unsafe", "candidates": []}),
        encoding="utf-8",
    )
    (run_dir / "artifact_index.json").write_text(
        json.dumps(
            {
                "run_id": "unsafe",
                "root": str(run_dir),
                "run_artifacts": {"report": "../secret.md"},
                "candidates": {},
            }
        ),
        encoding="utf-8",
    )
    client = TestClient(create_app(output_root=tmp_path))

    response = client.get("/api/runs/unsafe/artifact/report")

    assert response.status_code == 400
    assert response.json()["code"] == "artifact_index_error"


def test_candidate_artifact_endpoint_returns_missing_candidate_error(tmp_path: Path) -> None:
    client = TestClient(create_app(output_root=tmp_path))
    run = _create_run(client)

    response = client.get(f"/api/runs/{run['run_id']}/candidates/missing/artifact/musicxml")

    assert response.status_code == 400
    assert response.json()["code"] == "artifact_index_error"


def test_render_endpoint_honors_read_only_mode(tmp_path: Path) -> None:
    """Regression: read-only API mode must not create render artifacts."""
    write_client = TestClient(create_app(output_root=tmp_path))
    run = _create_run(write_client)
    run_id = cast(str, run["run_id"])
    candidate_id = _first_candidate_id(run)
    artifact_index = tmp_path / run_id / "artifact_index.json"
    artifact_index_before = artifact_index.read_text(encoding="utf-8")
    fake_musescore = _fake_musescore_bin(tmp_path)
    read_only_client = TestClient(
        create_app(
            output_root=tmp_path,
            read_only=True,
            musescore_bin=fake_musescore,
        )
    )

    response = read_only_client.post(
        f"/api/runs/{run_id}/candidates/{candidate_id}/render",
        json={"formats": ["pdf"]},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "read_only_mode"
    assert artifact_index.read_text(encoding="utf-8") == artifact_index_before
    assert not (tmp_path / run_id / "renders").exists()


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


def _fake_musescore_bin(tmp_path: Path) -> Path:
    executable = tmp_path / "fake-musescore"
    executable.write_text(
        """#!/usr/bin/env python3
from pathlib import Path
import sys

args = sys.argv[1:]
if "-o" not in args:
    raise SystemExit(2)
output_path = Path(args[args.index("-o") + 1])
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_bytes(b"%PDF-1.4\\n")
""",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    return executable
