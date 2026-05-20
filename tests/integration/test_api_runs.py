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


def test_run_upload_applies_score_profile_override(tmp_path: Path) -> None:
    client = TestClient(create_app(output_root=tmp_path))

    with Path("examples/melodies/bad_for_canon.musicxml").open("rb") as handle:
        response = client.post(
            "/api/runs",
            files={"file": ("bad_for_canon.musicxml", handle, "application/xml")},
            data={"engine": "strict", "top_k": "1", "score_profile": "permissive"},
        )

    assert response.status_code == 200, response.text
    payload = cast(dict[str, Any], response.json())
    config_summary = cast(dict[str, Any], payload["config_summary"])
    scoring = cast(dict[str, Any], config_summary["scoring"])
    candidates = cast(list[dict[str, Any]], payload["candidates"])
    metadata = cast(dict[str, Any], candidates[0]["metadata"])

    assert scoring["profile"] == "permissive"
    assert metadata["score_profile"] == "permissive"


def test_polish_endpoint_returns_lineaged_variants_for_real_run(tmp_path: Path) -> None:
    client = TestClient(create_app(output_root=tmp_path))

    with Path("examples/melodies/scale_c_major.musicxml").open("rb") as handle:
        run_response = client.post(
            "/api/runs",
            files={"file": ("scale_c_major.musicxml", handle, "application/xml")},
            data={"engine": "strict", "top_k": "1"},
        )

    assert run_response.status_code == 200, run_response.text
    run_payload = cast(dict[str, Any], run_response.json())
    run_id = cast(str, run_payload["run_id"])
    candidates = cast(list[dict[str, Any]], run_payload["candidates"])
    parent_candidate = candidates[0]
    candidate_id = cast(str, parent_candidate["candidate_id"])
    follower_bar = _first_pitched_bar(parent_candidate, role="follower")

    polish_response = client.post(
        f"/api/runs/{run_id}/candidates/{candidate_id}/polish",
        json={
            "bar_start": follower_bar,
            "bar_end": follower_bar,
            "lock_voice": "leader",
            "rewrite_voice": "follower",
            "max_variants": 2,
            "objective_preset": "reduce_repetition",
            "objective_overrides": {"repeated_note_penalty": 1.5},
        },
    )

    assert polish_response.status_code == 200, polish_response.text
    payload = cast(dict[str, Any], polish_response.json())
    summary = cast(dict[str, Any], payload["summary"])
    variants = cast(list[dict[str, Any]], payload["candidates"])
    assert summary["parent_candidate_id"] == candidate_id
    assert summary["edited_bars"] == [follower_bar]
    assert 0 < summary["returned_variants"] <= 2
    assert len(variants) == summary["returned_variants"]
    metadata = cast(dict[str, Any], variants[0]["metadata"])
    assert metadata["parent_candidate_id"] == candidate_id
    assert metadata["edited_bars"] == [follower_bar]
    assert metadata["rewrite_voice"] == "follower"


def test_polish_endpoint_reports_missing_candidate_as_diagnostic(tmp_path: Path) -> None:
    client = TestClient(create_app(output_root=tmp_path))

    with Path("examples/melodies/scale_c_major.musicxml").open("rb") as handle:
        run_response = client.post(
            "/api/runs",
            files={"file": ("scale_c_major.musicxml", handle, "application/xml")},
            data={"engine": "strict", "top_k": "1"},
        )

    run_id = cast(str, cast(dict[str, Any], run_response.json())["run_id"])

    response = client.post(
        f"/api/runs/{run_id}/candidates/missing/polish",
        json={"bar_start": 1, "bar_end": 1},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "polish_candidate_not_found"


def _first_pitched_bar(candidate: dict[str, Any], *, role: str) -> int:
    for note in cast(list[dict[str, Any]], candidate["notes"]):
        if note["role"] == role and note["pitch"] is not None:
            return cast(int, note["bar"])
    raise AssertionError(f"candidate has no pitched {role} note")


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
    client = TestClient(create_app(output_root=tmp_path, cors_origins=("http://localhost:5173",)))

    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
