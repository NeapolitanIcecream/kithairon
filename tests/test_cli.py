from __future__ import annotations

from typer.testing import CliRunner

from kithairon.cli import app


def test_version_command_prints_package_version() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "0.1.0" in result.stdout
