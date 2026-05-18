from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from typer.testing import CliRunner

from kithairon.cli import app


def _run_auto(input_path: str, out_dir: Path) -> dict[str, Any]:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "generate",
            input_path,
            "--out",
            str(out_dir),
            "--engine",
            "auto",
        ],
    )
    assert result.exit_code == 0, result.stdout
    return cast(dict[str, Any], json.loads((out_dir / "results.json").read_text()))


def test_auto_engine_keeps_good_input_on_strict_path(tmp_path: Path) -> None:
    out_dir = tmp_path / "auto_good"

    results = _run_auto("examples/melodies/scale_c_major.musicxml", out_dir)
    candidate_engines = [candidate["engine"] for candidate in results["candidates"]]

    assert results["engine"] == "auto"
    assert set(candidate_engines) == {"strict"}
    assert results["fallback_path"]["repair"]["triggered"] is False
    assert "Fallback path" in (out_dir / "report.md").read_text(encoding="utf-8")


def test_auto_engine_triggers_fallback_for_bad_input(tmp_path: Path) -> None:
    out_dir = tmp_path / "auto_bad"

    results = _run_auto("examples/melodies/bad_for_canon.musicxml", out_dir)
    candidate_engines = {candidate["engine"] for candidate in results["candidates"]}

    assert results["engine"] == "auto"
    assert candidate_engines.intersection({"repair", "solver"})
    assert results["fallback_path"]["repair"]["triggered"] is True
    assert "Fallback path" in (out_dir / "report.md").read_text(encoding="utf-8")
