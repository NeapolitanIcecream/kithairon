from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from typer.testing import CliRunner

from kithairon.cli import app

GOLDEN_DIR = Path(__file__).parents[1] / "golden"


def test_strict_scale_results_match_golden_snapshot(tmp_path: Path) -> None:
    out_dir = _generate_strict_scale(tmp_path)
    results = cast(
        dict[str, Any],
        json.loads((out_dir / "results.json").read_text(encoding="utf-8")),
    )
    expected = cast(
        dict[str, Any],
        json.loads((GOLDEN_DIR / "strict_scale_top_candidate.json").read_text(encoding="utf-8")),
    )

    assert _top_candidate_snapshot(results) == expected


def test_strict_scale_report_matches_golden_snapshot(tmp_path: Path) -> None:
    out_dir = _generate_strict_scale(tmp_path)
    actual = (out_dir / "report.md").read_text(encoding="utf-8").rstrip("\n")
    expected = (GOLDEN_DIR / "strict_scale_report.md").read_text(encoding="utf-8").rstrip("\n")

    assert actual == expected


def _generate_strict_scale(tmp_path: Path) -> Path:
    out_dir = tmp_path / "strict_scale"
    result = CliRunner().invoke(
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
    return out_dir


def _top_candidate_snapshot(results: dict[str, Any]) -> dict[str, Any]:
    candidates = cast(list[dict[str, Any]], results["candidates"])
    candidate = candidates[0]
    return {
        "engine": results["engine"],
        "candidate": {
            "id": candidate["id"],
            "rank": candidate["rank"],
            "engine": candidate["engine"],
            "strict_canon": candidate["strict_canon"],
            "score": candidate["score"],
            "quality_status": candidate["quality_status"],
            "transform_spec": candidate["transform_spec"],
            "score_breakdown": candidate["score_breakdown"],
            "violations": candidate["violations"],
            "outputs": candidate["outputs"],
        },
    }
