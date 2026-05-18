from __future__ import annotations

from pathlib import Path

from kithairon.adapters.music21_parse import parse_melody
from kithairon.config import GenerationConfig, InputConfig, KithaironConfig
from kithairon.engines.strict import generate_strict_candidates


def test_strict_engine_generates_candidates_from_example_musicxml() -> None:
    melody = parse_melody(
        Path("examples/melodies/scale_c_major.musicxml"),
        InputConfig(),
    )
    config = KithaironConfig(
        generation=GenerationConfig(
            engine="strict",
            top_k=2,
            max_candidates=4,
            transforms=("identity", "transposition"),
        )
    )

    candidates = generate_strict_candidates(melody, config)

    assert len(candidates) == 2
    assert all(candidate.strict_canon for candidate in candidates)
    assert all(candidate.voices[0].melody.source_path for candidate in candidates)
