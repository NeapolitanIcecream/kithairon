from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from kithairon.api.app import create_app
from kithairon.cli import app
from kithairon.polish import PolishRequest, polish_run_candidate


def test_polish_command_returns_variants_for_existing_run_candidate(tmp_path: Path) -> None:
    runner = CliRunner()
    out_dir = tmp_path / "strict"
    generate_result = runner.invoke(
        app,
        [
            "generate",
            "examples/melodies/scale_c_major.musicxml",
            "--out",
            str(out_dir),
            "--engine",
            "strict",
            "--top-k",
            "1",
        ],
    )
    assert generate_result.exit_code == 0, generate_result.stdout
    visualization = cast(
        dict[str, Any],
        json.loads((out_dir / "visualization.json").read_text(encoding="utf-8")),
    )
    candidates = cast(list[dict[str, Any]], visualization["candidates"])
    parent_candidate = candidates[0]
    candidate_id = cast(str, parent_candidate["candidate_id"])
    follower_bar = _first_pitched_bar(parent_candidate, role="follower")

    polish_result = runner.invoke(
        app,
        [
            "polish",
            str(out_dir),
            "--candidate",
            candidate_id,
            "--bars",
            f"{follower_bar}-{follower_bar}",
            "--lock-voice",
            "leader",
            "--preset",
            "reduce-repetition",
            "--top-k",
            "2",
        ],
    )

    assert polish_result.exit_code == 0, polish_result.stdout
    payload = cast(dict[str, Any], json.loads(polish_result.stdout))
    expected = polish_run_candidate(
        out_dir,
        candidate_id,
        PolishRequest(
            bar_start=follower_bar,
            bar_end=follower_bar,
            lock_voice="leader",
            max_variants=2,
            objective_preset="reduce_repetition",
        ),
    )

    assert payload["summary"]["parent_candidate_id"] == candidate_id
    assert payload["summary"]["returned_variants"] == expected.summary.returned_variants
    for candidate in cast(list[dict[str, Any]], payload["candidates"]):
        metadata = cast(dict[str, Any], candidate["metadata"])
        assert metadata["parent_candidate_id"] == candidate_id
        assert metadata["edited_bars"] == [follower_bar]
        assert metadata["rewrite_voice"] == "follower"


def test_polish_command_and_api_return_consistent_lineage(tmp_path: Path) -> None:
    runner = CliRunner()
    out_dir = tmp_path / "strict"
    generate_result = runner.invoke(
        app,
        [
            "generate",
            "examples/melodies/scale_c_major.musicxml",
            "--out",
            str(out_dir),
            "--engine",
            "strict",
            "--top-k",
            "1",
        ],
    )
    assert generate_result.exit_code == 0, generate_result.stdout
    visualization = cast(
        dict[str, Any],
        json.loads((out_dir / "visualization.json").read_text(encoding="utf-8")),
    )
    parent_candidate = cast(list[dict[str, Any]], visualization["candidates"])[0]
    candidate_id = cast(str, parent_candidate["candidate_id"])
    follower_bar = _first_pitched_bar(parent_candidate, role="follower")

    cli_result = runner.invoke(
        app,
        [
            "polish",
            str(out_dir),
            "--candidate",
            candidate_id,
            "--bars",
            str(follower_bar),
            "--lock-voice",
            "leader",
            "--rewrite-voice",
            "follower",
            "--top-k",
            "2",
        ],
    )
    assert cli_result.exit_code == 0, cli_result.stdout
    cli_payload = cast(dict[str, Any], json.loads(cli_result.stdout))

    client = TestClient(create_app(output_root=tmp_path))
    api_response = client.post(
        f"/api/runs/{out_dir.name}/candidates/{candidate_id}/polish",
        json={
            "bar_start": follower_bar,
            "bar_end": follower_bar,
            "lock_voice": "leader",
            "rewrite_voice": "follower",
            "max_variants": 2,
            "objective_preset": "general_polish",
        },
    )
    assert api_response.status_code == 200, api_response.text
    api_payload = cast(dict[str, Any], api_response.json())

    assert cli_payload["summary"] == api_payload["summary"]
    cli_variants = cast(list[dict[str, Any]], cli_payload["candidates"])
    api_variants = cast(list[dict[str, Any]], api_payload["candidates"])
    assert [variant["candidate_id"] for variant in cli_variants] == [
        variant["candidate_id"] for variant in api_variants
    ]
    assert [variant["metadata"] for variant in cli_variants] == [
        variant["metadata"] for variant in api_variants
    ]


def _first_pitched_bar(candidate: dict[str, Any], *, role: str) -> int:
    for note in cast(list[dict[str, Any]], candidate["notes"]):
        if note["role"] == role and note["pitch"] is not None:
            return cast(int, note["bar"])
    raise AssertionError(f"candidate has no pitched {role} note")
