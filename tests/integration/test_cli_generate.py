from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from typer.testing import CliRunner

from kithairon.cli import app


def test_generate_command_writes_strict_outputs(tmp_path: Path) -> None:
    out_dir = tmp_path / "strict"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "generate",
            "examples/melodies/scale_c_major.musicxml",
            "--out",
            str(out_dir),
            "--engine",
            "strict",
            "--top-k",
            "2",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = cast(dict[str, Any], json.loads(result.stdout))
    assert payload["status"] == "ok"
    assert payload["candidates"] == 2

    results_path = out_dir / "results.json"
    report_path = out_dir / "report.md"
    config_path = out_dir / "resolved_config.toml"
    visualization_path = out_dir / "visualization.json"
    artifact_index_path = out_dir / "artifact_index.json"
    assert results_path.exists()
    assert report_path.exists()
    assert config_path.exists()
    assert visualization_path.exists()
    assert artifact_index_path.exists()
    assert payload["visualization"] == str(visualization_path)
    assert payload["artifact_index"] == str(artifact_index_path)

    results = cast(dict[str, Any], json.loads(results_path.read_text(encoding="utf-8")))
    assert results["engine"] == "strict"
    assert len(results["candidates"]) == 2
    first_candidate = cast(dict[str, Any], results["candidates"][0])
    outputs = cast(dict[str, str], first_candidate["outputs"])
    assert first_candidate["strict_canon"] is True
    assert first_candidate["canon_label"] == "strict canon"
    assert (out_dir / outputs["musicxml"]).exists()
    assert (out_dir / outputs["midi"]).exists()
    assert "Top candidates" in report_path.read_text(encoding="utf-8")

    visualization = cast(
        dict[str, Any],
        json.loads(visualization_path.read_text(encoding="utf-8")),
    )
    assert visualization["run_id"] == out_dir.name
    assert visualization["input_name"] == "scale_c_major.musicxml"
    assert len(cast(list[object], visualization["candidates"])) == 2

    artifact_index = cast(
        dict[str, Any],
        json.loads(artifact_index_path.read_text(encoding="utf-8")),
    )
    assert cast(dict[str, str], artifact_index["run_artifacts"]) == {
        "report": "report.md",
        "results": "results.json",
        "resolved_config": "resolved_config.toml",
        "visualization": "visualization.json",
    }
    indexed_candidates = cast(dict[str, Any], artifact_index["candidates"])
    assert first_candidate["id"] in indexed_candidates


def test_generate_command_uses_suffixed_output_dir_when_existing_dir_is_nonempty(
    tmp_path: Path,
) -> None:
    out_dir = tmp_path / "strict"
    out_dir.mkdir()
    marker = out_dir / "keep.txt"
    marker.write_text("existing output", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
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

    assert result.exit_code == 0, result.stdout
    payload = cast(dict[str, Any], json.loads(result.stdout))
    actual_out = Path(cast(str, payload["out"]))

    assert actual_out == tmp_path / "strict-1"
    assert marker.exists()
    assert (actual_out / "results.json").exists()
    assert (actual_out / "visualization.json").exists()
    assert (actual_out / "artifact_index.json").exists()


def test_generate_command_overwrites_existing_output_dir_when_requested(
    tmp_path: Path,
) -> None:
    out_dir = tmp_path / "strict"
    out_dir.mkdir()
    marker = out_dir / "stale.txt"
    marker.write_text("stale output", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
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
            "--overwrite",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = cast(dict[str, Any], json.loads(result.stdout))

    assert payload["out"] == str(out_dir)
    assert not marker.exists()
    assert (out_dir / "results.json").exists()
    assert (out_dir / "visualization.json").exists()
    assert (out_dir / "artifact_index.json").exists()
