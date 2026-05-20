from __future__ import annotations

import pytest
from pydantic import ValidationError

from kithairon.polish.models import BarRange, PolishRequest, PolishResultDTO, PolishSummaryDTO


def test_polish_request_validates_selected_bar_range_and_voice_options() -> None:
    request = PolishRequest(
        bar_start=2,
        bar_end=4,
        lock_voice="leader",
        rewrite_voice="follower",
        max_variants=3,
        objective_preset="reduce_repetition",
    )

    assert request.bar_range == BarRange(start=2, end=4)
    assert request.bar_range.as_list() == [2, 3, 4]


def test_polish_request_rejects_reversed_bar_range() -> None:
    with pytest.raises(ValidationError, match="bar_end"):
        PolishRequest(bar_start=4, bar_end=2)


def test_polish_result_dto_serializes_summary_and_candidates() -> None:
    request = PolishRequest(bar_start=1, bar_end=1)
    result = PolishResultDTO(
        request=request,
        summary=PolishSummaryDTO(
            parent_candidate_id="strict_0001",
            edited_bars=[1],
            lock_voice="none",
            rewrite_voice="follower",
            objective_preset="general_polish",
            requested_variants=6,
            returned_variants=0,
            changed_notes=0,
        ),
        candidates=[],
    )

    assert result.model_dump(mode="json")["summary"]["parent_candidate_id"] == "strict_0001"
