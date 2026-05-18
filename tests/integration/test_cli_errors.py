from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from click.testing import Result
from typer.testing import CliRunner

from kithairon.cli import app
from kithairon.engines import solver as solver_module
from tests.music_helpers import chord_score, overlapping_score, write_score


def test_validate_missing_input_returns_compact_json_error(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["validate", str(tmp_path / "missing.musicxml")])

    payload = _error_payload(result)

    details = cast(dict[str, object], payload["details"])

    assert payload["code"] == "input_not_found"
    assert str(details["path"]).endswith("missing.musicxml")


def test_validate_unsupported_format_returns_clear_error(tmp_path: Path) -> None:
    path = tmp_path / "melody.txt"
    path.write_text("not a score", encoding="utf-8")

    result = CliRunner().invoke(app, ["validate", str(path)])

    payload = _error_payload(result)

    assert payload["code"] == "unsupported_input_format"
    assert cast(dict[str, object], payload["details"])["suffix"] == ".txt"


def test_validate_chord_input_returns_monophonic_error(tmp_path: Path) -> None:
    path = write_score(chord_score(), tmp_path / "chord.musicxml")

    result = CliRunner().invoke(app, ["validate", str(path)])

    payload = _error_payload(result)

    assert payload["code"] == "chord_not_allowed"


def test_validate_polyphonic_input_returns_monophonic_error(tmp_path: Path) -> None:
    path = write_score(overlapping_score(), tmp_path / "polyphonic.musicxml")

    result = CliRunner().invoke(app, ["validate", str(path)])

    payload = _error_payload(result)

    assert payload["code"] == "polyphonic_input"


def test_generate_solver_unavailable_returns_install_hint(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(solver_module, "_import_cp_model", lambda: None)

    result = CliRunner().invoke(
        app,
        [
            "generate",
            "examples/melodies/bad_for_canon.musicxml",
            "--out",
            str(tmp_path / "solver"),
            "--engine",
            "solver",
        ],
    )

    payload = _error_payload(result)
    details = cast(dict[str, object], payload["details"])

    assert payload["code"] == "solver_unavailable"
    assert details["install_command"] == "uv sync --extra solver"


def _error_payload(result: Result) -> dict[str, Any]:
    combined_output = result.stdout + result.stderr
    assert result.exit_code == 1, combined_output
    assert "Traceback" not in combined_output
    return cast(dict[str, Any], json.loads(result.stdout))
