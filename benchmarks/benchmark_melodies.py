"""Refresh repeatable melody benchmark observations."""

from __future__ import annotations

import argparse
import json
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any, cast

from kithairon.config import load_config
from kithairon.pipeline import run_generation

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_ROOT = REPO_ROOT / "examples" / "melodies"
DEFAULT_OUTPUT = REPO_ROOT / "benchmarks" / "benchmark_results.json"


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    input_name: str
    overrides: Mapping[str, object]
    listening_notes: str


CASES: tuple[BenchmarkCase, ...] = (
    BenchmarkCase(
        name="scale-strict",
        input_name="scale_c_major.musicxml",
        overrides={"generation": {"engine": "strict", "top_k": 3}},
        listening_notes="Small diatonic smoke fixture; top strict candidates should remain stable.",
    ),
    BenchmarkCase(
        name="folk-strict",
        input_name="folk_like_period.musicxml",
        overrides={"generation": {"engine": "strict", "top_k": 3}},
        listening_notes="Balanced phrase for checking whether ranking favors consonant delays.",
    ),
    BenchmarkCase(
        name="bad-repair",
        input_name="bad_for_canon.musicxml",
        overrides={"generation": {"engine": "repair", "top_k": 1}},
        listening_notes="Negative fixture; repair should visibly improve the best strict base.",
    ),
    BenchmarkCase(
        name="bad-solver",
        input_name="bad_for_canon.musicxml",
        overrides={
            "generation": {"engine": "solver", "top_k": 1},
            "solver": {"max_seconds": 1.0, "max_edited_notes": 3, "max_candidates_in": 4},
        },
        listening_notes="Solver fixture; edit plan should stay short and objective status visible.",
    ),
    BenchmarkCase(
        name="bad-auto",
        input_name="bad_for_canon.musicxml",
        overrides={
            "generation": {"engine": "auto", "top_k": 4},
            "solver": {"enabled": True, "max_seconds": 1.0, "max_candidates_in": 4},
        },
        listening_notes=(
            "Auto fallback fixture; at least one relaxed candidate should remain visible."
        ),
    ),
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to write benchmark_results.json.",
    )
    args = parser.parse_args()

    payload = refresh_benchmarks()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def refresh_benchmarks() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="kithairon-benchmarks-") as temp_dir:
        output_root = Path(temp_dir)
        return {
            "schema_version": 1,
            "generated_at": datetime.now(UTC).isoformat(),
            "cases": [run_case(case, output_root) for case in CASES],
        }


def run_case(case: BenchmarkCase, output_root: Path) -> dict[str, object]:
    config = load_config(overrides=case.overrides)
    input_path = EXAMPLE_ROOT / case.input_name
    started = perf_counter()
    generation = run_generation(
        input_path,
        output_root / case.name,
        config,
        overwrite_output=True,
    )
    runtime_seconds = round(perf_counter() - started, 4)
    candidates = cast(list[dict[str, Any]], generation.results["candidates"])
    top_candidate = candidates[0] if candidates else {}
    metadata = _mapping(top_candidate.get("metadata"))
    objective_details = _mapping(metadata.get("objective_details"))
    edit_plan = metadata.get("edit_plan")

    return {
        "name": case.name,
        "input": case.input_name,
        "engine": generation.results["engine"],
        "candidate_count": len(candidates),
        "candidate_engines": sorted({str(candidate.get("engine")) for candidate in candidates}),
        "relaxed_candidate_count": sum(
            1 for candidate in candidates if candidate.get("strict_canon") is False
        ),
        "top_candidate_id": top_candidate.get("id"),
        "top_candidate_engine": top_candidate.get("engine"),
        "top_score": top_candidate.get("score"),
        "quality_status": top_candidate.get("quality_status"),
        "strict_canon": top_candidate.get("strict_canon"),
        "runtime_seconds": runtime_seconds,
        "edit_count": len(edit_plan) if isinstance(edit_plan, list) else 0,
        "solver_status": objective_details.get("status"),
        "solver_wall_time_seconds": objective_details.get("wall_time_seconds"),
        "listening_notes": case.listening_notes,
    }


def _mapping(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    mapped = cast(Mapping[object, object], value)
    return {str(key): item for key, item in mapped.items()}


if __name__ == "__main__":
    main()
