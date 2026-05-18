from __future__ import annotations

from fractions import Fraction
from typing import cast

from kithairon.config import GenerationConfig, KithaironConfig
from kithairon.engines.strict import generate_strict_candidates
from kithairon.ir import Melody, NoteEvent
from kithairon.transforms.apply import apply_transform


def _melody() -> Melody:
    return Melody(
        events=(
            NoteEvent(id="n1", pitch=60, start=Fraction(0), duration=Fraction(1)),
            NoteEvent(id="n2", pitch=62, start=Fraction(1), duration=Fraction(1)),
            NoteEvent(id="n3", pitch=64, start=Fraction(2), duration=Fraction(1)),
        ),
        time_signature="4/4",
        tempo_bpm=100,
        key_hint="C major",
    )


def _config() -> KithaironConfig:
    return KithaironConfig(
        generation=GenerationConfig(
            engine="strict",
            top_k=3,
            max_candidates=6,
            delays=(Fraction(1),),
            intervals=(0, 12),
            transforms=("identity", "transposition"),
        )
    )


def test_strict_engine_generates_ranked_strict_candidates() -> None:
    candidates = generate_strict_candidates(_melody(), _config())

    assert 1 <= len(candidates) <= 3
    assert all(candidate.engine == "strict" for candidate in candidates)
    assert all(candidate.strict_canon for candidate in candidates)
    assert [candidate.metadata["rank"] for candidate in candidates] == [1, 2, 3]
    assert all(candidate.score >= 0 for candidate in candidates)
    assert all("score_breakdown" in candidate.metadata for candidate in candidates)


def test_strict_engine_follower_is_exact_transform_of_input_melody() -> None:
    source = _melody()
    candidate = generate_strict_candidates(source, _config())[0]

    expected_follower = apply_transform(source, candidate.transform_spec)

    assert candidate.voices[0].name == "leader"
    assert candidate.voices[1].name == "follower"
    assert candidate.voices[1].melody.events == expected_follower.events


def test_strict_engine_marks_transform_metadata() -> None:
    candidate = generate_strict_candidates(_melody(), _config())[0]
    transform = cast(dict[str, object], candidate.metadata["transform"])

    assert transform["delay"] == "1"
    assert transform["transform_mode"] in {"identity", "transposition"}
