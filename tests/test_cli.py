from __future__ import annotations

import json
from typing import Any, cast

from typer.testing import CliRunner

from kithairon.cli import app


def test_version_command_prints_package_version() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


def test_help_command_lists_primary_commands() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "validate" in result.stdout
    assert "generate" in result.stdout
    assert "config" in result.stdout


def test_config_resolve_json_smoke() -> None:
    result = CliRunner().invoke(
        app,
        [
            "config",
            "resolve",
            "--format",
            "json",
            "--engine",
            "repair",
            "--top-k",
            "2",
        ],
    )

    assert result.exit_code == 0
    payload = cast(dict[str, Any], json.loads(result.stdout))
    generation = cast(dict[str, Any], payload["generation"])

    assert generation["engine"] == "repair"
    assert generation["top_k"] == 2
