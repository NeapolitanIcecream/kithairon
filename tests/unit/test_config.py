from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from typing import Any, cast

import pytest
from typer.testing import CliRunner

from kithairon.cli import app
from kithairon.config import KithaironConfig, load_config
from kithairon.errors import ConfigError


def test_default_config_matches_initial_generation_plan() -> None:
    config = KithaironConfig()

    assert config.input.chord_policy == "error"
    assert config.input.part_policy == "first"
    assert config.input.max_denominator == 48
    assert config.generation.engine == "auto"
    assert config.generation.top_k == 8
    assert config.generation.delays == (Fraction(1), Fraction(2), Fraction(4), Fraction(8))
    assert config.generation.rhythm_scales == (Fraction(1), Fraction(2), Fraction(1, 2))


def test_fraction_fields_serialize_stably_to_json() -> None:
    dumped = KithaironConfig().to_json_dict()
    generation = cast(dict[str, Any], dumped["generation"])

    assert generation["delays"] == ["1", "2", "4", "8"]
    assert generation["rhythm_scales"] == ["1", "2", "1/2"]


def test_load_config_merges_toml_with_section_defaults(tmp_path: Path) -> None:
    config_path = tmp_path / "canon.toml"
    config_path.write_text(
        """
[input]
chord_policy = "top_note"

[generation]
top_k = 3
delays = ["1/2", "2"]
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.input.chord_policy == "top_note"
    assert config.input.part_policy == "first"
    assert config.generation.top_k == 3
    assert config.generation.delays == (Fraction(1, 2), Fraction(2))
    assert config.generation.engine == "auto"


def test_cli_overrides_config_file_and_writes_resolved_toml(tmp_path: Path) -> None:
    runner = CliRunner()
    config_path = tmp_path / "canon.toml"
    out_path = tmp_path / "resolved_config.toml"
    config_path.write_text(
        """
[input]
chord_policy = "error"

[generation]
top_k = 2
engine = "auto"
""",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "config",
            "resolve",
            "--config",
            str(config_path),
            "--out",
            str(out_path),
            "--chord-policy",
            "bottom-note",
            "--engine",
            "strict",
            "--top-k",
            "9",
        ],
    )

    assert result.exit_code == 0
    resolved = out_path.read_text(encoding="utf-8")
    assert 'chord_policy = "bottom_note"' in resolved
    assert 'engine = "strict"' in resolved
    assert "top_k = 9" in resolved


def test_invalid_config_error_has_machine_readable_diagnostic(tmp_path: Path) -> None:
    config_path = tmp_path / "bad.toml"
    config_path.write_text(
        """
[input]
chord_policy = "middle_note"
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError) as raised:
        load_config(config_path)

    diagnostic = raised.value.to_diagnostic()
    details = cast(dict[str, Any], diagnostic["details"])
    assert diagnostic["code"] == "config_invalid"
    assert details["source"] == str(config_path)
