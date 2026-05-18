from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from kithairon.adapters.music21_parse import parse_melody
from kithairon.config import InputConfig, KithaironConfig
from kithairon.engines.auto import generate_auto_candidates


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
