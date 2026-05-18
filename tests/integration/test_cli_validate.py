from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from typer.testing import CliRunner

from kithairon.cli import app
from tests.music_helpers import chord_score, melody_score, write_score


def test_validate_command_reports_parsed_musicxml(tmp_path: Path) -> None:
    path = write_score(melody_score(), tmp_path / "melody.musicxml")
    runner = CliRunner()

    result = runner.invoke(app, ["validate", str(path)])

    assert result.exit_code == 0
    payload = cast(dict[str, Any], json.loads(result.stdout))
    assert payload["status"] == "ok"
    assert payload["events"] == 4
    assert payload["time_signature"] == "3/4"


def test_validate_command_honors_chord_policy_override(tmp_path: Path) -> None:
    path = write_score(chord_score(), tmp_path / "chord.musicxml")
    runner = CliRunner()

    result = runner.invoke(app, ["validate", str(path), "--chord-policy", "top-note"])

    assert result.exit_code == 0
    payload = cast(dict[str, Any], json.loads(result.stdout))
    assert payload["status"] == "ok"
    assert payload["events"] == 1
