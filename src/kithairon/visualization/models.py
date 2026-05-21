"""Pydantic DTOs for Kithairon visualization payloads."""

from __future__ import annotations

from fractions import Fraction
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from kithairon.config import format_fraction

type NoteRoleDTO = Literal["leader", "follower", "unknown"]
type TransformOriginDTO = Literal["input", "strict_transform", "repair", "solver", "unknown"]
type ViolationCategoryDTO = Literal[
    "consonance",
    "parallel_motion",
    "range",
    "crossing",
    "melody",
    "cadence",
    "similarity",
    "repair",
    "other",
]
type RepairActionKindDTO = Literal[
    "octave_displacement",
    "pitch_replacement",
    "passing_tone",
    "rest_insertion",
    "duration_adjustment",
    "solver_assignment",
    "unknown",
]
type EngineDTO = Literal["strict", "repair", "solver", "auto"]
type ViolationSeverityDTO = Literal["hard", "soft", "info"]
type ExperimentVariantStatusDTO = Literal["undecided", "kept", "rejected"]
type CadenceStrengthDTO = Literal["strong", "moderate", "weak"]
type CadenceTypeDTO = Literal[
    "open_phrase",
    "half_cadence_tendency",
    "authentic_close_tendency",
    "weak_close",
    "ambiguous_close",
]
type BassMotionLabelDTO = Literal["static", "stepwise", "active"]
type PhraseWarningKindDTO = Literal["repeated_note_plateau", "flat_sequence"]
type PhraseWarningVoiceRoleDTO = Literal["leader", "follower", "both", "unknown"]


class VisualizationModel(BaseModel):
    """Base model for serialized visualization contracts."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class RationalDTO(VisualizationModel):
    text: str
    value: float


class NoteVizDTO(VisualizationModel):
    event_id: str
    ir_event_id: str
    voice_id: str
    role: NoteRoleDTO = "unknown"
    pitch: int | None
    pitch_name: str | None
    start_q: RationalDTO
    duration_q: RationalDTO
    end_q: RationalDTO
    bar: int | None
    beat: RationalDTO | None
    velocity: int | None = None
    source_event_id: str | None = None
    transform_origin: TransformOriginDTO = "unknown"
    repair_action_id: str | None = None
    score_element_id: str | None = None


class ViolationVizDTO(VisualizationModel):
    violation_id: str
    rule_id: str
    severity: ViolationSeverityDTO
    penalty: float
    message: str
    bar: int | None
    beat: RationalDTO | None
    start_q: RationalDTO | None = None
    end_q: RationalDTO | None = None
    voice_ids: list[str]
    event_ids: list[str]
    ir_event_ids: list[str] = Field(default_factory=list)
    related_event_ids: list[str] = Field(default_factory=list)
    category: ViolationCategoryDTO = "other"


class ScoreBreakdownDTO(VisualizationModel):
    total: float
    by_category: dict[str, float] = Field(default_factory=dict)
    by_rule: dict[str, float] = Field(default_factory=dict)
    bonuses: dict[str, float] = Field(default_factory=dict)


class MusicalityMetricDTO(VisualizationModel):
    key: str
    label: str
    raw_value: float
    normalized_value: float
    weight: float
    higher_is_better: bool


class MusicalityBreakdownDTO(VisualizationModel):
    total: float
    metrics: list[MusicalityMetricDTO]
    raw_values: dict[str, float] = Field(default_factory=dict)
    normalized_values: dict[str, float] = Field(default_factory=dict)
    weights: dict[str, float] = Field(default_factory=dict)


class RepairActionDTO(VisualizationModel):
    action_id: str
    kind: RepairActionKindDTO = "unknown"
    original_event_id: str | None = None
    new_event_id: str | None = None
    message: str
    start_q: RationalDTO | None = None
    bar: int | None = None
    beat: RationalDTO | None = None


class TransformVizDTO(VisualizationModel):
    engine: EngineDTO
    strict_canon: bool
    label: str
    delay_q: RationalDTO | None = None
    interval: int | None = None
    transform_mode: str | None = None
    inversion_axis: int | None = None
    rhythm_scale: str | None = None


class PhraseWarningDTO(VisualizationModel):
    kind: PhraseWarningKindDTO
    voice_role: PhraseWarningVoiceRoleDTO
    event_ids: list[str]
    message: str


def _empty_phrase_warnings() -> list[PhraseWarningDTO]:
    return []


class PhraseSpanDTO(VisualizationModel):
    phrase_id: str
    bar_start: int
    bar_end: int
    start_q: RationalDTO
    end_q: RationalDTO
    event_ids: list[str]
    note_count: int
    label: str
    high_point_event_id: str | None = None
    high_point_pitch: int | None = None
    arrival_event_id: str | None = None
    arrival_pitch: int | None = None
    repeated_note_plateaus: list[str] = Field(default_factory=list)
    flat_sequence_warning: bool = False
    warnings: list[str] = Field(default_factory=list)
    warning_items: list[PhraseWarningDTO] = Field(default_factory=_empty_phrase_warnings)


class CadenceSummaryDTO(VisualizationModel):
    cadence_id: str
    bar: int
    beat: RationalDTO
    strength: CadenceStrengthDTO
    cadence_type: CadenceTypeDTO = "ambiguous_close"
    final_interval: str
    bass_motion: int | None
    upper_motion: int | None
    event_ids: list[str]
    label: str
    rationale: str


class BassSupportDTO(VisualizationModel):
    voice_id: str
    bar_start: int
    bar_end: int
    unique_pitch_count: int
    repeated_note_ratio: float
    stepwise_motion_ratio: float
    average_abs_motion: float
    static_bars: list[int]
    static_bass: bool
    motion_label: BassMotionLabelDTO
    strong_beat_support_event_ids: list[str] = Field(default_factory=list)
    root_support_proxy: float = 0.0
    sustained_foundation_score: float = 0.0
    bass_independence_score: float = 0.0


def _empty_cadences() -> list[CadenceSummaryDTO]:
    return []


class CandidateAnalysisDTO(VisualizationModel):
    phrases: list[PhraseSpanDTO]
    cadence: CadenceSummaryDTO | None = None
    cadences: list[CadenceSummaryDTO] = Field(default_factory=_empty_cadences)
    bass_support: BassSupportDTO | None = None


def _empty_repair_actions() -> list[RepairActionDTO]:
    return []


class CandidateVizDTO(VisualizationModel):
    candidate_id: str
    rank: int | None
    title: str
    transform: TransformVizDTO
    score: ScoreBreakdownDTO
    musicality: MusicalityBreakdownDTO | None = None
    analysis: CandidateAnalysisDTO | None = None
    notes: list[NoteVizDTO]
    violations: list[ViolationVizDTO]
    repair_actions: list[RepairActionDTO] = Field(default_factory=_empty_repair_actions)
    artifacts: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, object] = Field(default_factory=dict)


class RunSummaryDTO(VisualizationModel):
    run_id: str
    input_name: str
    created_at: str
    config_summary: dict[str, object]
    artifacts: dict[str, str] = Field(default_factory=dict)
    candidates: list[CandidateVizDTO]


class ExperimentVariantDTO(VisualizationModel):
    candidate_id: str
    status: ExperimentVariantStatusDTO = "undecided"
    candidate: CandidateVizDTO


class ExperimentDTO(VisualizationModel):
    experiment_id: str
    source_candidate_id: str
    source_request: dict[str, object]
    created_at: str
    notes: str = ""
    variants: list[ExperimentVariantDTO]


class ExperimentCreateDTO(VisualizationModel):
    source_candidate_id: str
    source_request: dict[str, object]
    candidates: list[CandidateVizDTO]


class ExperimentPatchDTO(VisualizationModel):
    notes: str | None = None
    variant_status: dict[str, ExperimentVariantStatusDTO] = Field(default_factory=dict)


def rational_dto(value: Fraction) -> RationalDTO:
    """Serialize a Fraction with exact text and frontend-friendly float value."""
    return RationalDTO(text=format_fraction(value), value=float(value))


def optional_rational_dto(value: Fraction | None) -> RationalDTO | None:
    """Serialize an optional Fraction for fields that may be unavailable."""
    return rational_dto(value) if value is not None else None


def note_viz_event_id(voice_id: str, ir_event_id: str) -> str:
    """Return the visualization-layer unique event id for a voice event."""
    return f"{voice_id}:{ir_event_id}"
