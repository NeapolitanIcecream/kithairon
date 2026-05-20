"""Pydantic contracts for local phrase polish requests and results."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from kithairon.visualization.models import CandidateVizDTO, ExperimentDTO

type LockVoice = Literal["leader", "follower", "none"]
type RewriteVoice = Literal["leader", "follower", "auto"]
type SearchMode = Literal["local_polish", "rewrite_selected_voice"]
type ObjectivePreset = Literal[
    "reduce_repetition",
    "smooth_bass",
    "strengthen_cadence",
    "general_polish",
]


class PolishModel(BaseModel):
    """Base model for serialized polish contracts."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class BarRange(PolishModel):
    start: int = Field(ge=1)
    end: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_order(self) -> BarRange:
        if self.end < self.start:
            raise ValueError("bar range end must be greater than or equal to start")
        return self

    def as_list(self) -> list[int]:
        return list(range(self.start, self.end + 1))


class PolishObjectiveWeights(PolishModel):
    repeated_note_penalty: float | None = Field(default=None, ge=0)
    leap_penalty: float | None = Field(default=None, ge=0)
    bass_smoothness_penalty: float | None = Field(default=None, ge=0)
    cadence_motion_reward: float | None = Field(default=None, ge=0)


class PolishRequest(PolishModel):
    bar_start: int = Field(ge=1)
    bar_end: int = Field(ge=1)
    lock_voice: LockVoice = "none"
    rewrite_voice: RewriteVoice = "auto"
    max_variants: int = Field(default=6, ge=1, le=50)
    objective_preset: ObjectivePreset = "general_polish"
    objective_overrides: PolishObjectiveWeights = Field(default_factory=PolishObjectiveWeights)
    search_mode: SearchMode = "local_polish"
    allow_rhythm_change: bool = False

    @model_validator(mode="after")
    def validate_request(self) -> PolishRequest:
        if self.bar_end < self.bar_start:
            raise ValueError("bar_end must be greater than or equal to bar_start")
        if self.search_mode == "rewrite_selected_voice" and self.rewrite_voice == "auto":
            raise ValueError("rewrite_selected_voice mode requires an explicit rewrite_voice")
        return self

    @property
    def bar_range(self) -> BarRange:
        return BarRange(start=self.bar_start, end=self.bar_end)


class PolishSummaryDTO(PolishModel):
    parent_candidate_id: str
    edited_bars: list[int]
    lock_voice: LockVoice
    rewrite_voice: Literal["leader", "follower"]
    objective_preset: ObjectivePreset
    search_mode: SearchMode = "local_polish"
    allow_rhythm_change: bool = False
    requested_variants: int
    returned_variants: int
    changed_notes: int


class PolishResultDTO(PolishModel):
    request: PolishRequest
    summary: PolishSummaryDTO
    candidates: list[CandidateVizDTO]
    experiment: ExperimentDTO | None = None
