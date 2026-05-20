from __future__ import annotations

import pytest
from pydantic import ValidationError

from kithairon.feedback.models import FeedbackTarget, FeedbackTranslateRequest


def test_feedback_request_serializes_text_candidate_and_target() -> None:
    request = FeedbackTranslateRequest(
        text="cadence weak",
        candidate_id="strict_0001",
        target=FeedbackTarget(bar_start=7, bar_end=8),
    )

    assert request.model_dump(mode="json") == {
        "text": "cadence weak",
        "candidate_id": "strict_0001",
        "target": {"bar_start": 7, "bar_end": 8},
    }


def test_feedback_target_rejects_reversed_bar_range() -> None:
    with pytest.raises(ValidationError, match="bar_end"):
        FeedbackTarget(bar_start=8, bar_end=7)
