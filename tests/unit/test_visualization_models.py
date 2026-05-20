from __future__ import annotations

from fractions import Fraction

import pytest
from pydantic import ValidationError

from kithairon.visualization.models import (
    CandidateVizDTO,
    MusicalityBreakdownDTO,
    MusicalityMetricDTO,
    NoteVizDTO,
    RunSummaryDTO,
    ScoreBreakdownDTO,
    TransformVizDTO,
    ViolationVizDTO,
    note_viz_event_id,
    rational_dto,
)


def test_rational_dto_preserves_exact_text_and_float_value() -> None:
    assert rational_dto(Fraction(3, 2)).model_dump() == {"text": "3/2", "value": 1.5}
    assert rational_dto(Fraction(2)).model_dump() == {"text": "2", "value": 2.0}


def test_note_event_id_is_unique_per_voice_even_when_ir_id_is_shared() -> None:
    assert note_viz_event_id("leader", "n0001") == "leader:n0001"
    assert note_viz_event_id("follower", "n0001") == "follower:n0001"


def test_note_viz_forbids_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        NoteVizDTO.model_validate(
            {
                "event_id": "leader:n0001",
                "ir_event_id": "n0001",
                "voice_id": "leader",
                "role": "leader",
                "pitch": 60,
                "pitch_name": "C4",
                "start_q": rational_dto(Fraction(0)),
                "duration_q": rational_dto(Fraction(1)),
                "end_q": rational_dto(Fraction(1)),
                "bar": 1,
                "beat": rational_dto(Fraction(1)),
                "unexpected": True,
            }
        )


def test_violation_viz_keeps_visual_and_ir_event_ids_separate() -> None:
    violation = ViolationVizDTO(
        violation_id="v0001",
        rule_id="range",
        severity="hard",
        penalty=10.0,
        message="Follower is outside the allowed range.",
        bar=2,
        beat=rational_dto(Fraction(1)),
        voice_ids=["follower"],
        event_ids=["follower:n0001"],
        ir_event_ids=["n0001"],
        category="range",
    )

    assert violation.event_ids == ["follower:n0001"]
    assert violation.ir_event_ids == ["n0001"]


def test_candidate_and_run_artifacts_are_separate_contracts() -> None:
    transform = TransformVizDTO(
        engine="strict",
        strict_canon=True,
        label="strict canon",
        delay_q=rational_dto(Fraction(1)),
        interval=7,
        transform_mode="transposition",
    )
    candidate = CandidateVizDTO(
        candidate_id="strict_0001",
        rank=1,
        title="Candidate 1",
        transform=transform,
        score=ScoreBreakdownDTO(total=92.5),
        notes=[],
        violations=[],
        artifacts={
            "musicxml": "/api/runs/run-1/candidates/strict_0001/musicxml",
            "midi": "/api/runs/run-1/candidates/strict_0001/midi",
        },
    )

    assert set(candidate.artifacts) == {"musicxml", "midi"}

    run = RunSummaryDTO(
        run_id="run-1",
        input_name="scale.musicxml",
        created_at="2026-05-18T00:00:00Z",
        config_summary={},
        artifacts={
            "report": "/api/runs/run-1/artifact/report",
            "results": "/api/runs/run-1/artifact/results",
        },
        candidates=[candidate],
    )

    assert set(run.artifacts) == {"report", "results"}
    assert run.candidates[0].candidate_id == "strict_0001"


def test_musicality_breakdown_serializes_raw_normalized_and_weighted_metrics() -> None:
    breakdown = MusicalityBreakdownDTO(
        total=82.5,
        metrics=[
            MusicalityMetricDTO(
                key="repeated_note_density",
                label="Repeated-note density",
                raw_value=0.25,
                normalized_value=0.75,
                weight=0.2,
                higher_is_better=False,
            )
        ],
        raw_values={"repeated_note_density": 0.25},
        normalized_values={"repeated_note_density": 0.75},
        weights={"repeated_note_density": 0.2},
    )

    payload = breakdown.model_dump(mode="json")

    assert payload["total"] == 82.5
    assert payload["metrics"][0]["key"] == "repeated_note_density"
