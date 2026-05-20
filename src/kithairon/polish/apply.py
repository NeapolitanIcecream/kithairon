"""Adapters between persisted visualization DTOs and polish search results."""

from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction
from typing import Literal, cast

from kithairon.config import QualityConfig
from kithairon.ir import (
    CanonCandidate,
    EngineName,
    Melody,
    NoteEvent,
    RuleViolation,
    TransformMode,
    TransformSpec,
    Voice,
    VoiceRole,
)
from kithairon.polish.models import PolishRequest, PolishResultDTO, PolishSummaryDTO
from kithairon.polish.search import search_polish_variants
from kithairon.visualization.materialize import materialize_candidate
from kithairon.visualization.models import CandidateVizDTO, NoteVizDTO, ViolationVizDTO


def polish_candidate_dto(
    candidate_dto: CandidateVizDTO,
    request: PolishRequest,
    *,
    score_profile: str = "pop-lite",
    quality: QualityConfig | None = None,
) -> PolishResultDTO:
    candidate = candidate_from_dto(candidate_dto)
    variants = search_polish_variants(
        candidate,
        request,
        score_profile=score_profile,
        quality=quality,
    )
    rewrite_voice = _result_rewrite_voice(variants, request, candidate_dto)
    result_candidates = [materialize_candidate(variant) for variant in variants]
    return PolishResultDTO(
        request=request,
        summary=PolishSummaryDTO(
            parent_candidate_id=candidate.id,
            edited_bars=request.bar_range.as_list(),
            lock_voice=request.lock_voice,
            rewrite_voice=rewrite_voice,
            objective_preset=request.objective_preset,
            search_mode=request.search_mode,
            allow_rhythm_change=request.allow_rhythm_change,
            requested_variants=request.max_variants,
            returned_variants=len(result_candidates),
            changed_notes=_changed_note_count(candidate_dto, result_candidates),
        ),
        candidates=result_candidates,
    )


def candidate_from_dto(candidate: CandidateVizDTO) -> CanonCandidate:
    voices = _voices_from_notes(candidate.notes, metadata=candidate.metadata)
    return CanonCandidate(
        id=candidate.candidate_id,
        voices=voices,
        transform_spec=TransformSpec(
            delay=_fraction_from_rational_text(candidate.transform.delay_q.text)
            if candidate.transform.delay_q is not None
            else Fraction(0),
            interval=candidate.transform.interval or 0,
            transform_mode=cast(TransformMode, candidate.transform.transform_mode or "identity"),
            inversion_axis=candidate.transform.inversion_axis,
            rhythm_scale=Fraction(candidate.transform.rhythm_scale or "1"),
        ),
        engine=cast(EngineName, candidate.transform.engine),
        strict_canon=candidate.transform.strict_canon,
        score=candidate.score.total,
        violations=tuple(_violation_from_dto(violation) for violation in candidate.violations),
        metadata={
            **candidate.metadata,
            "score_breakdown": {
                "penalties": [
                    {"rule_id": rule_id, "weighted_penalty": penalty}
                    for rule_id, penalty in candidate.score.by_rule.items()
                ],
                "bonuses": candidate.score.bonuses,
            },
        },
    )


def _voices_from_notes(
    notes: list[NoteVizDTO],
    *,
    metadata: Mapping[str, object],
) -> tuple[Voice, Voice]:
    leaders = _voice_from_notes(notes, role="leader", metadata=metadata)
    followers = _voice_from_notes(notes, role="follower", metadata=metadata)
    return leaders, followers


def _voice_from_notes(
    notes: list[NoteVizDTO],
    *,
    role: VoiceRole,
    metadata: Mapping[str, object],
) -> Voice:
    role_notes = sorted(
        (note for note in notes if note.role == role),
        key=lambda note: (Fraction(note.start_q.text), note.ir_event_id),
    )
    voice_name = role_notes[0].voice_id if role_notes else role
    time_signature = _time_signature_from_metadata(metadata)
    events = tuple(
        NoteEvent(
            id=note.ir_event_id,
            pitch=note.pitch,
            start=Fraction(note.start_q.text),
            duration=Fraction(note.duration_q.text),
            velocity=64 if note.velocity is None else note.velocity,
        )
        for note in role_notes
    )
    return Voice(
        name=voice_name,
        role=role,
        melody=Melody(events=events, time_signature=time_signature),
    )


def _time_signature_from_metadata(metadata: Mapping[str, object]) -> str:
    value = metadata.get("time_signature")
    return value if isinstance(value, str) else "4/4"


def _violation_from_dto(violation: ViolationVizDTO) -> RuleViolation:
    return RuleViolation(
        rule_id=violation.rule_id,
        severity=violation.severity,
        penalty=violation.penalty,
        message=violation.message,
        bar=violation.bar,
        beat=Fraction(violation.beat.text) if violation.beat is not None else None,
        voice_ids=tuple(violation.voice_ids),
        event_ids=tuple(violation.ir_event_ids),
    )


def _fraction_from_rational_text(text: str) -> Fraction:
    return Fraction(text)


def _result_rewrite_voice(
    variants: tuple[CanonCandidate, ...],
    request: PolishRequest,
    _candidate_dto: CandidateVizDTO,
) -> Literal["leader", "follower"]:
    if variants:
        value = variants[0].metadata.get("rewrite_voice")
        if value in {"leader", "follower"}:
            return cast(Literal["leader", "follower"], value)
    if request.rewrite_voice in {"leader", "follower"}:
        return cast(Literal["leader", "follower"], request.rewrite_voice)
    if request.lock_voice == "follower":
        return "leader"
    return "follower"


def _changed_note_count(
    parent: CandidateVizDTO,
    variants: list[CandidateVizDTO],
) -> int:
    parent_pitches = {note.event_id: note.pitch for note in parent.notes}
    changed: set[str] = set()
    for variant in variants:
        for note in variant.notes:
            if parent_pitches.get(note.event_id) != note.pitch:
                changed.add(note.event_id)
    return len(changed)
