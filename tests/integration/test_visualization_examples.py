from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from kithairon.config import load_config
from kithairon.pipeline import run_generation


@pytest.mark.parametrize("input_path", sorted(Path("examples/melodies").glob("*.musicxml")))
def test_musicxml_examples_generate_visualization_artifacts(
    tmp_path: Path,
    input_path: Path,
) -> None:
    config = load_config(
        overrides={
            "generation": {
                "engine": "strict",
                "top_k": 1,
            }
        }
    )

    generation = run_generation(
        input_path,
        tmp_path / input_path.stem,
        config,
        overwrite_output=True,
    )

    assert generation.visualization_path.exists()
    assert generation.artifact_index_path.exists()
    visualization = cast(
        dict[str, Any],
        json.loads(generation.visualization_path.read_text(encoding="utf-8")),
    )
    artifact_index = cast(
        dict[str, Any],
        json.loads(generation.artifact_index_path.read_text(encoding="utf-8")),
    )
    assert visualization["run_id"] == input_path.stem
    assert visualization["candidates"]
    assert artifact_index["run_artifacts"]["visualization"] == "visualization.json"
