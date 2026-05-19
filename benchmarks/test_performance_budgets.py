from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from kithairon.adapters.music21_parse import parse_melody
from kithairon.api.app import create_app
from kithairon.config import load_config
from kithairon.engines.strict import generate_strict_candidate_pool
from kithairon.pipeline import run_generation


def test_strict_enumeration_size_and_runtime_budget() -> None:
    config = load_config(overrides={"generation": {"engine": "strict"}})
    melody = parse_melody(Path("examples/melodies/scale_c_major.musicxml"), config.input)

    started = perf_counter()
    candidates = generate_strict_candidate_pool(melody, config)
    runtime_seconds = perf_counter() - started

    assert len(candidates) == 156
    assert runtime_seconds < 1.5


def test_repair_generation_runtime_budget(tmp_path: Path) -> None:
    config = load_config(overrides={"generation": {"engine": "repair", "top_k": 1}})

    started = perf_counter()
    generation = run_generation(
        Path("examples/melodies/bad_for_canon.musicxml"),
        tmp_path / "repair",
        config,
        overwrite_output=True,
    )
    runtime_seconds = perf_counter() - started
    top_candidate = generation.candidates[0]

    assert runtime_seconds < 8.0
    assert top_candidate.engine == "repair"
    assert top_candidate.metadata["edit_plan"]


def test_solver_timeout_metadata_respects_configured_budget(tmp_path: Path) -> None:
    pytest.importorskip("ortools")
    config = load_config(
        overrides={
            "generation": {"engine": "solver", "top_k": 1},
            "solver": {"max_seconds": 0.5, "max_edited_notes": 3, "max_candidates_in": 4},
        }
    )

    started = perf_counter()
    generation = run_generation(
        Path("examples/melodies/bad_for_canon.musicxml"),
        tmp_path / "solver",
        config,
        overwrite_output=True,
    )
    runtime_seconds = perf_counter() - started
    metadata = generation.candidates[0].metadata
    objective_details = cast(dict[str, Any], metadata["objective_details"])

    assert runtime_seconds < 6.0
    assert objective_details["max_time_seconds"] == 0.5
    assert objective_details["status"] in {"OPTIMAL", "FEASIBLE"}


def test_api_generation_latency_budget(tmp_path: Path) -> None:
    client = TestClient(create_app(output_root=tmp_path))

    with Path("examples/melodies/scale_c_major.musicxml").open("rb") as handle:
        started = perf_counter()
        response = client.post(
            "/api/runs",
            files={"file": ("scale_c_major.musicxml", handle, "application/xml")},
            data={"engine": "strict", "top_k": "1"},
        )
        runtime_seconds = perf_counter() - started

    assert response.status_code == 200, response.text
    assert runtime_seconds < 4.0
