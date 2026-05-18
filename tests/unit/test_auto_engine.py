from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from kithairon.adapters.music21_parse import parse_melody
from kithairon.config import InputConfig, KithaironConfig, QualityConfig
from kithairon.engines.auto import generate_auto_candidates
from kithairon.ir import CanonCandidate, Melody


def test_auto_engine_marks_strict_only_path_for_good_input() -> None:
    melody = parse_melody(Path("examples/melodies/scale_c_major.musicxml"), InputConfig())

    candidates = generate_auto_candidates(melody, KithaironConfig())
    fallback_path = cast(dict[str, Any], candidates[0].metadata["fallback_path"])

    assert candidates
    assert {candidate.engine for candidate in candidates} == {"strict"}
    assert fallback_path["repair"]["triggered"] is False


def test_auto_engine_includes_relaxed_candidate_for_bad_input() -> None:
    melody = parse_melody(Path("examples/melodies/bad_for_canon.musicxml"), InputConfig())

    candidates = generate_auto_candidates(melody, KithaironConfig())
    fallback_path = cast(dict[str, Any], candidates[0].metadata["fallback_path"])

    assert candidates
    assert {candidate.engine for candidate in candidates}.intersection({"repair", "solver"})
    assert fallback_path["repair"]["triggered"] is True


def test_auto_engine_does_not_run_solver_when_solver_is_disabled(
    monkeypatch: Any,
) -> None:
    melody = parse_melody(Path("examples/melodies/bad_for_canon.musicxml"), InputConfig())
    config = KithaironConfig(
        quality=QualityConfig(auto_repair_threshold=100, auto_solver_threshold=100)
    )
    solver_called = False

    def fake_repair_candidates(
        _melody: Melody,
        _config: KithaironConfig,
    ) -> tuple[CanonCandidate, ...]:
        return ()

    def fake_solver_candidates(
        _melody: Melody,
        _config: KithaironConfig,
    ) -> tuple[CanonCandidate, ...]:
        nonlocal solver_called
        solver_called = True
        return ()

    monkeypatch.setattr("kithairon.engines.auto.solver_available", lambda: True)
    monkeypatch.setattr("kithairon.engines.auto.generate_repair_candidates", fake_repair_candidates)
    monkeypatch.setattr("kithairon.engines.auto.generate_solver_candidates", fake_solver_candidates)

    candidates = generate_auto_candidates(melody, config)
    fallback_path = cast(dict[str, Any], candidates[0].metadata["fallback_path"])

    assert solver_called is False
    assert fallback_path["solver"]["triggered"] is False
