from __future__ import annotations

from fractions import Fraction
from typing import cast

from kithairon.config import GenerationConfig, KithaironConfig, RepairConfig
from kithairon.engines.repair import generate_repair_candidates
from kithairon.ir import Melody, NoteEvent


def _bad_melody() -> Melody:
    return Melody(
        events=(
            NoteEvent(id="n1", pitch=60, start=Fraction(0), duration=Fraction(1)),
            NoteEvent(id="n2", pitch=61, start=Fraction(1), duration=Fraction(1)),
            NoteEvent(id="n3", pitch=63, start=Fraction(2), duration=Fraction(1)),
            NoteEvent(id="n4", pitch=66, start=Fraction(3), duration=Fraction(1)),
        ),
        time_signature="4/4",
        tempo_bpm=92,
        key_hint="C major",
    )


def _repair_config() -> KithaironConfig:
    return KithaironConfig(
        generation=GenerationConfig(
            engine="repair",
            top_k=2,
            max_candidates=8,
            delays=(Fraction(1),),
            intervals=(-1, 1, 2),
            transforms=("transposition",),
        ),
        repair=RepairConfig(beam_width=4, max_steps=4, max_edited_notes=2),
    )


def test_repair_engine_outputs_relaxed_candidate_with_better_score() -> None:
    repaired = generate_repair_candidates(_bad_melody(), _repair_config())

    assert repaired
    candidate = repaired[0]
    assert candidate.engine == "repair"
    assert candidate.strict_canon is False
    assert candidate.score > cast(float, candidate.metadata["base_strict_score"])
    assert candidate.metadata["base_strict_candidate_id"]
    assert candidate.metadata["edit_plan"]


def test_repair_engine_records_follower_pitch_edits() -> None:
    candidate = generate_repair_candidates(_bad_melody(), _repair_config())[0]
    edit_plan = cast(list[dict[str, object]], candidate.metadata["edit_plan"])

    assert edit_plan[0]["voice"] == "follower"
    assert edit_plan[0]["operation"] in {"nearest_consonance", "octave_shift"}
    assert edit_plan[0]["event_id"]
    assert edit_plan[0]["from_pitch"] != edit_plan[0]["to_pitch"]
    assert candidate.metadata["bad_windows"]
