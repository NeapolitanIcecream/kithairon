from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from typer.testing import CliRunner

from kithairon.cli import app


def test_generate_repair_writes_relaxed_candidate_with_edit_plan(tmp_path: Path) -> None:
    out_dir = tmp_path / "repair"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "generate",
            "examples/melodies/bad_for_canon.musicxml",
            "--out",
            str(out_dir),
            "--engine",
            "repair",
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

    assert results["engine"] == "repair"
    assert first_candidate["engine"] == "repair"
    assert first_candidate["strict_canon"] is False
    assert first_candidate["canon_label"] == "relaxed canon"
    assert first_candidate["score"] > metadata["base_strict_score"]
    assert metadata["edit_plan"]
    assert (out_dir / outputs["musicxml"]).exists()
    assert (out_dir / outputs["midi"]).exists()
    report = (out_dir / "report.md").read_text(encoding="utf-8")
    assert "relaxed canon" in report
    assert "Edit plan" in report
