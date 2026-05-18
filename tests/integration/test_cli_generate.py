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
    assert results_path.exists()
    assert report_path.exists()
    assert config_path.exists()

    results = cast(dict[str, Any], json.loads(results_path.read_text(encoding="utf-8")))
    assert results["engine"] == "strict"
    assert len(results["candidates"]) == 2
    first_candidate = cast(dict[str, Any], results["candidates"][0])
    outputs = cast(dict[str, str], first_candidate["outputs"])
    assert (out_dir / outputs["musicxml"]).exists()
    assert (out_dir / outputs["midi"]).exists()
    assert "Top candidates" in report_path.read_text(encoding="utf-8")
