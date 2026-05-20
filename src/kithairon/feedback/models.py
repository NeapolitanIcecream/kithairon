"""Structured feedback contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from kithairon.polish.models import PolishRequest

type FeedbackIntent = Literal[
    "too_mechanical",
    "too_repetitive",
    "bass_too_static",
    "cadence_weak",
    "melody_too_jumpy",
    "voices_too_rhythmically_similar",
]


class FeedbackModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FeedbackTarget(FeedbackModel):
    bar_start: int | None = Field(default=None, ge=1)
    bar_end: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_order(self) -> FeedbackTarget:
        if (
            self.bar_start is not None
            and self.bar_end is not None
            and self.bar_end < self.bar_start
        ):
            raise ValueError("bar_end must be greater than or equal to bar_start")
        return self


class FeedbackTranslateRequest(FeedbackModel):
    text: str = Field(min_length=1)
    candidate_id: str | None = None
    target: FeedbackTarget = Field(default_factory=FeedbackTarget)


class SuggestedPolishAction(FeedbackModel):
    action_id: str
    label: str
    reason: str
    request: PolishRequest


class FeedbackTranslationDTO(FeedbackModel):
    input_text: str
    candidate_id: str | None
    intents: list[FeedbackIntent]
    target: FeedbackTarget
    actions: list[SuggestedPolishAction]
    explanation: str
