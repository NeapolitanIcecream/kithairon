"""End-to-end generation pipeline."""

from __future__ import annotations

import json
import shutil
from collections.abc import Mapping
from dataclasses import dataclass, replace
from fractions import Fraction
from pathlib import Path
from typing import Any, cast

from kithairon.adapters.music21_parse import parse_melody
from kithairon.config import KithaironConfig, format_fraction, write_resolved_config
from kithairon.engines.auto import generate_auto_candidates
from kithairon.engines.repair import generate_repair_candidates
from kithairon.engines.solver import generate_solver_candidates
from kithairon.engines.strict import generate_strict_candidates, transform_spec_to_dict
from kithairon.errors import GenerationError, OutputError
from kithairon.export import CandidateExportPaths, write_candidate_exports
from kithairon.ir import CanonCandidate, Melody, RuleViolation
from kithairon.report import report_candidate_rows, write_report


@dataclass(frozen=True)
class GenerationRun:
    output_dir: Path
    results_path: Path
    report_path: Path
    resolved_config_path: Path
    candidates: tuple[CanonCandidate, ...]
    results: Mapping[str, Any]


def run_generation(
    input_path: Path,
    output_dir: Path,
    config: KithaironConfig,
    *,
    overwrite_output: bool = False,
) -> GenerationRun:
    engine = config.generation.engine
    output_dir = _resolve_output_dir(output_dir, overwrite_output=overwrite_output)
    melody = parse_melody(input_path, config.input)
    candidates = _generate_candidates(melody, config, engine)
    _prepare_output_dir(output_dir, overwrite_output=overwrite_output)
    candidates_with_outputs = _write_candidate_outputs(candidates, output_dir)

    resolved_config_path = output_dir / "resolved_config.toml"
    results_path = output_dir / "results.json"
    report_path = output_dir / "report.md"
    write_resolved_config(config, resolved_config_path)

    results = _results_payload(
        input_path=input_path,
        output_dir=output_dir,
        config=config,
        engine=engine,
        candidates=candidates_with_outputs,
    )
    results_path.write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(
        {
            **results,
            "candidates": report_candidate_rows(results["candidates"]),
        },
        report_path,
    )
    return GenerationRun(
        output_dir=output_dir,
        results_path=results_path,
        report_path=report_path,
        resolved_config_path=resolved_config_path,
        candidates=candidates_with_outputs,
        results=results,
    )


def _resolve_output_dir(output_dir: Path, *, overwrite_output: bool) -> Path:
    if not output_dir.exists():
        return output_dir
    if overwrite_output or _is_empty_dir(output_dir):
        return output_dir
    return _next_available_output_dir(output_dir)


def _prepare_output_dir(output_dir: Path, *, overwrite_output: bool) -> None:
    try:
        if output_dir.exists() and overwrite_output:
            _remove_output_path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise OutputError(
            f"Could not prepare output directory: {output_dir}",
            code="output_directory_unavailable",
            details={"path": str(output_dir), "error": str(exc)},
        ) from exc


def _remove_output_path(output_path: Path) -> None:
    if output_path.is_dir():
        shutil.rmtree(output_path)
    else:
        output_path.unlink()


def _is_empty_dir(path: Path) -> bool:
    return path.is_dir() and not any(path.iterdir())


def _next_available_output_dir(output_dir: Path) -> Path:
    for index in range(1, 1000):
        candidate = output_dir.with_name(f"{output_dir.name}-{index}")
        if not candidate.exists():
            return candidate
    raise OutputError(
        f"Could not find an available output directory next to: {output_dir}",
        code="output_directory_collision",
        details={"path": str(output_dir), "attempts": 999},
    )


def _generate_candidates(
    melody: object,
    config: KithaironConfig,
    engine: str,
) -> tuple[CanonCandidate, ...]:
    if not isinstance(melody, Melody):
        raise TypeError("expected Melody")
    if engine == "auto":
        return generate_auto_candidates(melody, config)
    if engine == "strict":
        return generate_strict_candidates(melody, config)
    if engine == "repair":
        candidates = generate_repair_candidates(melody, config)
        if not candidates:
            raise GenerationError(
                "Repair engine could not improve any strict candidate.",
                code="repair_no_candidates",
                details={"engine": engine},
            )
        return candidates
    if engine == "solver":
        candidates = generate_solver_candidates(melody, config)
        if not candidates:
            raise GenerationError(
                "CP-SAT solver did not find a feasible relaxed canon candidate.",
                code="solver_no_solution",
                details={
                    "engine": engine,
                    "max_seconds": config.solver.max_seconds,
                    "max_edited_notes": config.solver.max_edited_notes,
                },
            )
        return candidates
    raise GenerationError(
        f"Generation engine is not implemented yet: {engine}",
        code="generation_engine_not_implemented",
        details={"engine": engine},
    )


def _write_candidate_outputs(
    candidates: tuple[CanonCandidate, ...],
    output_dir: Path,
) -> tuple[CanonCandidate, ...]:
    candidate_dir = output_dir / "candidates"
    return tuple(
        _write_single_candidate(candidate, candidate_dir, output_dir) for candidate in candidates
    )


def _write_single_candidate(
    candidate: CanonCandidate,
    candidate_dir: Path,
    output_dir: Path,
) -> CanonCandidate:
    rank = _metadata_int(candidate.metadata, "rank")
    stem = _candidate_stem(candidate, rank)
    paths = write_candidate_exports(candidate, candidate_dir, stem=stem)
    return replace(
        candidate,
        metadata={
            **candidate.metadata,
            "outputs": _relative_output_paths(paths, output_dir),
        },
    )


def _results_payload(
    *,
    input_path: Path,
    output_dir: Path,
    config: KithaironConfig,
    engine: str,
    candidates: tuple[CanonCandidate, ...],
) -> dict[str, Any]:
    return {
        "input_path": str(input_path),
        "engine": engine,
        "output_dir": str(output_dir),
        "resolved_config": config.to_json_dict(),
        "candidates": [_candidate_to_result(candidate) for candidate in candidates],
        **_fallback_payload(candidates),
    }


def _candidate_to_result(candidate: CanonCandidate) -> dict[str, Any]:
    score_breakdown = _mapping(candidate.metadata.get("score_breakdown", {}))
    outputs = _mapping(candidate.metadata.get("outputs", {}))
    return {
        "id": candidate.id,
        "rank": candidate.metadata.get("rank"),
        "engine": candidate.engine,
        "strict_canon": candidate.strict_canon,
        "canon_label": _canon_label(candidate),
        "score": candidate.score,
        "quality_status": candidate.metadata.get("quality_status"),
        "transform_spec": transform_spec_to_dict(candidate.transform_spec),
        "violations": [_violation_to_dict(violation) for violation in candidate.violations],
        "score_breakdown": score_breakdown,
        "outputs": outputs,
        "metadata": _metadata_without_expanded_sections(candidate.metadata),
    }


def _canon_label(candidate: CanonCandidate) -> str:
    return "strict canon" if candidate.strict_canon else "relaxed canon"


def _fallback_payload(candidates: tuple[CanonCandidate, ...]) -> dict[str, Any]:
    if not candidates:
        return {}
    fallback_path = candidates[0].metadata.get("fallback_path")
    if isinstance(fallback_path, Mapping):
        mapped = cast(Mapping[object, object], fallback_path)
        return {"fallback_path": _jsonable(mapped)}
    return {}


def _violation_to_dict(violation: RuleViolation) -> dict[str, Any]:
    return {
        "rule_id": violation.rule_id,
        "severity": violation.severity,
        "penalty": violation.penalty,
        "message": violation.message,
        "bar": violation.bar,
        "beat": _jsonable(violation.beat),
        "voice_ids": list(violation.voice_ids),
        "event_ids": list(violation.event_ids),
        "data": _jsonable(violation.data),
    }


def _metadata_without_expanded_sections(metadata: Mapping[str, object]) -> dict[str, Any]:
    return {
        key: _jsonable(value)
        for key, value in metadata.items()
        if key not in {"outputs", "score_breakdown"}
    }


def _relative_output_paths(paths: CandidateExportPaths, output_dir: Path) -> dict[str, str]:
    return {
        "musicxml": str(paths.musicxml.relative_to(output_dir)),
        "midi": str(paths.midi.relative_to(output_dir)),
    }


def _candidate_stem(candidate: CanonCandidate, rank: int) -> str:
    spec = candidate.transform_spec
    delay = format_fraction(spec.delay).replace("/", "_")
    interval = str(spec.interval).replace("-", "m")
    return f"{rank:03d}_{candidate.engine}_{spec.transform_mode}_delay_{delay}_interval_{interval}"


def _jsonable(value: object) -> Any:
    if isinstance(value, Fraction):
        return format_fraction(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        mapped = cast(Mapping[object, object], value)
        return {str(key): _jsonable(item) for key, item in mapped.items()}
    if isinstance(value, tuple | list):
        sequence = cast(tuple[object, ...] | list[object], value)
        return [_jsonable(item) for item in sequence]
    return value


def _mapping(value: object) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        mapped = cast(Mapping[object, object], value)
        return {str(key): _jsonable(item) for key, item in mapped.items()}
    return {}


def _metadata_int(metadata: Mapping[str, object], key: str) -> int:
    value = metadata.get(key)
    if isinstance(value, int):
        return value
    return 0
