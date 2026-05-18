from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from typer.testing import CliRunner

from kithairon.cli import app


def test_generate_solver_writes_relaxed_candidate_with_objective_details(tmp_path: Path) -> None:
    out_dir = tmp_path / "solver"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "generate",
            "examples/melodies/bad_for_canon.musicxml",
            "--out",
            str(out_dir),
            "--engine",
            "solver",
            "--top-k",
            "1",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = cast(dict[str, Any], json.loads(result.stdout))
    assert payload["status"] == "ok"
    assert payload["candidates"] >= 1

    results = cast(
        dict[str, Any],
        json.loads((out_dir / "results.json").read_text(encoding="utf-8")),
    )
    first_candidate = cast(dict[str, Any], results["candidates"][0])
    metadata = cast(dict[str, Any], first_candidate["metadata"])
    outputs = cast(dict[str, str], first_candidate["outputs"])

    assert results["engine"] == "solver"
    assert first_candidate["engine"] == "solver"
    assert first_candidate["strict_canon"] is False
    assert first_candidate["canon_label"] == "relaxed canon"
    assert metadata["edit_plan"]
    assert metadata["objective_details"]
    assert (out_dir / outputs["musicxml"]).exists()
    assert (out_dir / outputs["midi"]).exists()

    report = (out_dir / "report.md").read_text(encoding="utf-8")
    assert "relaxed canon" in report
    assert "Edit plan" in report
    assert "Objective details" in report
