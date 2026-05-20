"""Convert core canon candidates into visualization DTOs."""

from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction
from typing import cast

from kithairon.analysis.timeline import parse_time_signature
from kithairon.ir import CanonCandidate, NoteEvent, RuleViolation, Voice
from kithairon.visualization.models import (
    CandidateVizDTO,
    NoteVizDTO,
    RationalDTO,
    RepairActionDTO,
    RepairActionKindDTO,
    RunSummaryDTO,
    ScoreBreakdownDTO,
    TransformOriginDTO,
    TransformVizDTO,
    ViolationCategoryDTO,
    ViolationVizDTO,
    note_viz_event_id,
    optional_rational_dto,
    rational_dto,
)

PITCH_CLASS_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def materialize_candidate(
    candidate: CanonCandidate,
    *,
    artifacts: Mapping[str, str] | None = None,
) -> CandidateVizDTO:
    """Create a visualization DTO for one generated candidate."""
    artifact_urls = dict(artifacts or _string_mapping(candidate.metadata.get("outputs")))
    repair_actions = _repair_actions(candidate)
    edited_event_ids = {
        action.original_event_id.split(":", maxsplit=1)[1]
        for action in repair_actions
        if action.original_event_id is not None and ":" in action.original_event_id
    }
    notes = [
        _note_viz(
            voice=voice,
            event=event,
            candidate=candidate,
            edited_event_ids=edited_event_ids,
        )
        for voice in candidate.voices
        for event in voice.melody.events
    ]
    return CandidateVizDTO(
        candidate_id=candidate.id,
        rank=_int_or_none(candidate.metadata.get("rank")),
        title=_candidate_title(candidate),
        transform=_transform_viz(candidate),
        score=_score_breakdown(candidate),
        notes=notes,
        violations=[
            _violation_viz(candidate, violation, index)
            for index, violation in enumerate(candidate.violations, start=1)
        ],
        repair_actions=repair_actions,
        artifacts=artifact_urls,
        metadata={
            **_jsonable_mapping(candidate.metadata, exclude={"outputs", "score_breakdown"}),
            "time_signature": candidate.voices[0].melody.time_signature,
        },
    )


def materialize_run_summary(
    *,
    run_id: str,
    input_name: str,
    created_at: str,
    config_summary: Mapping[str, object],
    run_artifacts: Mapping[str, str],
    candidates: tuple[CanonCandidate, ...],
) -> RunSummaryDTO:
    """Create the visualization summary for one generation run."""
    return RunSummaryDTO(
        run_id=run_id,
        input_name=input_name,
        created_at=created_at,
        config_summary=dict(config_summary),
        artifacts=dict(run_artifacts),
        candidates=[materialize_candidate(candidate) for candidate in candidates],
    )


def _note_viz(
    *,
    voice: Voice,
    event: NoteEvent,
    candidate: CanonCandidate,
    edited_event_ids: set[str],
) -> NoteVizDTO:
    start = event.start
    end = event.start + event.duration
    bar, beat = _metric_position(start, voice.melody.time_signature)
    return NoteVizDTO(
        event_id=note_viz_event_id(voice.name, event.id),
        ir_event_id=event.id,
        voice_id=voice.name,
        role=voice.role,
        pitch=event.pitch,
        pitch_name=_pitch_name(event.pitch),
        start_q=rational_dto(start),
        duration_q=rational_dto(event.duration),
        end_q=rational_dto(end),
        bar=bar,
        beat=beat,
        velocity=event.velocity,
        source_event_id=_source_event_id(candidate, voice, event),
        transform_origin=_transform_origin(candidate, voice, event, edited_event_ids),
        repair_action_id=(
            _repair_action_id(candidate, event.id) if event.id in edited_event_ids else None
        ),
        score_element_id=None,
    )


def _violation_viz(
    candidate: CanonCandidate,
    violation: RuleViolation,
    index: int,
) -> ViolationVizDTO:
    related_events = _events_for_violation(candidate, violation)
    start_q, end_q = _violation_span(related_events)
    bar = violation.bar
    beat = optional_rational_dto(violation.beat)
    if (bar is None or beat is None) and start_q is not None:
        derived_bar, derived_beat = _metric_position(
            _fraction_from_rational(start_q),
            candidate.voices[0].melody.time_signature,
        )
        bar = bar or derived_bar
        beat = beat or derived_beat

    return ViolationVizDTO(
        violation_id=f"{candidate.id}:v{index:04d}:{violation.rule_id}",
        rule_id=violation.rule_id,
        severity=violation.severity,
        penalty=violation.penalty,
        message=violation.message,
        bar=bar,
        beat=beat,
        start_q=start_q,
        end_q=end_q,
        voice_ids=list(violation.voice_ids),
        event_ids=_visual_event_ids(candidate, violation),
        ir_event_ids=list(violation.event_ids),
        related_event_ids=[],
        category=_category_for_rule(violation.rule_id),
    )


def _repair_actions(candidate: CanonCandidate) -> list[RepairActionDTO]:
    actions: list[RepairActionDTO] = []
    for raw_action in _metadata_mappings(candidate.metadata.get("edit_plan")):
        event_id = _string_or_none(raw_action.get("event_id"))
        if event_id is None:
            continue
        voice_id = _string_or_none(raw_action.get("voice")) or "follower"
        visual_event_id = note_viz_event_id(voice_id, event_id)
        event = _event_by_visual_id(candidate, visual_event_id)
        bar, beat = _action_position(candidate, raw_action, event)
        actions.append(
            RepairActionDTO(
                action_id=_repair_action_id(candidate, event_id),
                kind=_repair_action_kind(candidate, raw_action),
                original_event_id=visual_event_id,
                new_event_id=visual_event_id,
                message=_repair_action_message(raw_action),
                start_q=rational_dto(event.start) if event is not None else None,
                bar=bar,
                beat=beat,
            )
        )
    return actions


def _transform_viz(candidate: CanonCandidate) -> TransformVizDTO:
    spec = candidate.transform_spec
    return TransformVizDTO(
        engine=candidate.engine,
        strict_canon=candidate.strict_canon,
        label=_candidate_label(candidate),
        delay_q=rational_dto(spec.delay),
        interval=spec.interval,
        transform_mode=spec.transform_mode,
        inversion_axis=spec.inversion_axis,
        rhythm_scale=_fraction_text(spec.rhythm_scale),
    )


def _score_breakdown(candidate: CanonCandidate) -> ScoreBreakdownDTO:
    raw_breakdown = _object_mapping(candidate.metadata.get("score_breakdown"))
    by_rule: dict[str, float] = {}
    by_category: dict[str, float] = {}
    penalties = raw_breakdown.get("penalties")
    if isinstance(penalties, list | tuple):
        penalty_items = cast(list[object] | tuple[object, ...], penalties)
        for item in penalty_items:
            penalty = _object_mapping(item)
            rule_id = _string_or_none(penalty.get("rule_id"))
            weighted = _float_or_none(penalty.get("weighted_penalty"))
            if rule_id is None or weighted is None:
                continue
            by_rule[rule_id] = round(by_rule.get(rule_id, 0.0) + weighted, 2)
            category = _category_for_rule(rule_id)
            by_category[category] = round(by_category.get(category, 0.0) + weighted, 2)
    else:
        for violation in candidate.violations:
            by_rule[violation.rule_id] = round(
                by_rule.get(violation.rule_id, 0.0) + violation.penalty,
                2,
            )
            category = _category_for_rule(violation.rule_id)
            by_category[category] = round(by_category.get(category, 0.0) + violation.penalty, 2)

    return ScoreBreakdownDTO(
        total=candidate.score,
        by_category=by_category,
        by_rule=by_rule,
        bonuses=_float_mapping(raw_breakdown.get("bonuses")),
    )


def _events_for_violation(
    candidate: CanonCandidate,
    violation: RuleViolation,
) -> list[tuple[Voice, NoteEvent]]:
    events: list[tuple[Voice, NoteEvent]] = []
    voice_filter = set(violation.voice_ids)
    for raw_event_id in violation.event_ids:
        for voice in candidate.voices:
            if voice_filter and voice.name not in voice_filter:
                continue
            for event in voice.melody.events:
                if event.id == raw_event_id:
                    events.append((voice, event))
    return events


def _violation_span(
    events: list[tuple[Voice, NoteEvent]],
) -> tuple[RationalDTO | None, RationalDTO | None]:
    if not events:
        return None, None
    start = min(event.start for _, event in events)
    end = max(event.start + event.duration for _, event in events)
    return rational_dto(start), rational_dto(end)


def _visual_event_ids(candidate: CanonCandidate, violation: RuleViolation) -> list[str]:
    visual_ids: list[str] = []
    for voice, event in _events_for_violation(candidate, violation):
        event_id = note_viz_event_id(voice.name, event.id)
        if event_id not in visual_ids:
            visual_ids.append(event_id)
    return visual_ids


def _source_event_id(candidate: CanonCandidate, voice: Voice, event: NoteEvent) -> str | None:
    if voice.role != "follower":
        return None
    leader = candidate.voices[0]
    if any(source.id == event.id for source in leader.melody.events):
        return note_viz_event_id(leader.name, event.id)
    return None


def _transform_origin(
    candidate: CanonCandidate,
    voice: Voice,
    event: NoteEvent,
    edited_event_ids: set[str],
) -> TransformOriginDTO:
    if voice.role == "leader":
        return "input"
    if event.id in edited_event_ids and candidate.engine == "solver":
        return "solver"
    if event.id in edited_event_ids:
        return "repair"
    return "strict_transform"


def _action_position(
    candidate: CanonCandidate,
    action: Mapping[str, object],
    event: NoteEvent | None,
) -> tuple[int | None, RationalDTO | None]:
    bar = _int_or_none(action.get("bar"))
    beat = optional_rational_dto(_fraction_or_none(action.get("beat")))
    if (bar is None or beat is None) and event is not None:
        derived_bar, derived_beat = _metric_position(
            event.start,
            candidate.voices[0].melody.time_signature,
        )
        bar = bar or derived_bar
        beat = beat or derived_beat
    return bar, beat


def _event_by_visual_id(candidate: CanonCandidate, visual_event_id: str) -> NoteEvent | None:
    voice_id, _, ir_event_id = visual_event_id.partition(":")
    for voice in candidate.voices:
        if voice.name != voice_id:
            continue
        for event in voice.melody.events:
            if event.id == ir_event_id:
                return event
    return None


def _metric_position(
    offset: Fraction,
    time_signature: str,
) -> tuple[int | None, RationalDTO | None]:
    try:
        meter = parse_time_signature(time_signature)
    except ValueError:
        return None, None
    offset_in_bar = offset - ((offset // meter.bar_length) * meter.bar_length)
    beat = (offset_in_bar / meter.beat_length) + 1
    return int(offset // meter.bar_length) + 1, rational_dto(beat)


def _category_for_rule(rule_id: str) -> ViolationCategoryDTO:
    if rule_id in {"strong_beat_consonance", "weak_beat_dissonance"}:
        return "consonance"
    if rule_id == "parallel_perfect":
        return "parallel_motion"
    if rule_id == "range":
        return "range"
    if rule_id == "voice_crossing":
        return "crossing"
    if rule_id == "large_leap":
        return "melody"
    if rule_id == "cadence_stability":
        return "cadence"
    if rule_id.startswith("repair"):
        return "repair"
    return "other"


def _repair_action_kind(
    candidate: CanonCandidate,
    action: Mapping[str, object],
) -> RepairActionKindDTO:
    operation = _string_or_none(action.get("operation")) or ""
    if candidate.engine == "solver" or operation == "cp_sat_pitch_assignment":
        return "solver_assignment"
    if operation == "octave_shift":
        return "octave_displacement"
    if operation in {"nearest_consonance", "pitch_replacement"}:
        return "pitch_replacement"
    return "unknown"


def _repair_action_message(action: Mapping[str, object]) -> str:
    operation = _string_or_none(action.get("operation")) or "edit"
    from_pitch = action.get("from_pitch")
    to_pitch = action.get("to_pitch")
    if isinstance(from_pitch, int) and isinstance(to_pitch, int):
        return f"{operation}: {from_pitch} -> {to_pitch}"
    return operation


def _repair_action_id(candidate: CanonCandidate, event_id: str) -> str:
    return f"{candidate.id}:repair:{event_id}"


def _candidate_title(candidate: CanonCandidate) -> str:
    rank = _int_or_none(candidate.metadata.get("rank"))
    return f"Candidate {rank}" if rank is not None else candidate.id


def _candidate_label(candidate: CanonCandidate) -> str:
    return "strict canon" if candidate.strict_canon else "relaxed canon"


def _pitch_name(pitch: int | None) -> str | None:
    if pitch is None:
        return None
    return f"{PITCH_CLASS_NAMES[pitch % 12]}{(pitch // 12) - 1}"


def _fraction_text(value: Fraction) -> str:
    return str(rational_dto(value).text)


def _fraction_from_rational(value: RationalDTO) -> Fraction:
    return Fraction(value.text)


def _fraction_or_none(value: object) -> Fraction | None:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value, 1)
    if isinstance(value, float):
        return Fraction(str(value))
    if isinstance(value, str) and value:
        try:
            return Fraction(value)
        except ValueError:
            return None
    return None


def _int_or_none(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _float_or_none(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def _string_or_none(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _object_mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        mapped = cast(Mapping[object, object], value)
        return {key: item for key, item in mapped.items() if isinstance(key, str)}
    return {}


def _string_mapping(value: object) -> Mapping[str, str]:
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, str] = {}
    for key, item in cast(Mapping[object, object], value).items():
        if isinstance(key, str) and isinstance(item, str):
            result[key] = item
    return result


def _float_mapping(value: object) -> dict[str, float]:
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, float] = {}
    for key, item in cast(Mapping[object, object], value).items():
        numeric = _float_or_none(item)
        if isinstance(key, str) and numeric is not None:
            result[key] = numeric
    return result


def _metadata_mappings(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, list | tuple):
        return ()
    sequence = cast(list[object] | tuple[object, ...], value)
    mappings: list[Mapping[str, object]] = []
    for item in sequence:
        if not isinstance(item, Mapping):
            continue
        mapped = cast(Mapping[object, object], item)
        mappings.append({key: value for key, value in mapped.items() if isinstance(key, str)})
    return tuple(mappings)


def _jsonable_mapping(
    value: Mapping[str, object],
    *,
    exclude: set[str],
) -> dict[str, object]:
    return {key: _jsonable(item) for key, item in value.items() if key not in exclude}


def _jsonable(value: object) -> object:
    if isinstance(value, Fraction):
        return _fraction_text(value)
    if isinstance(value, Mapping):
        mapped = cast(Mapping[object, object], value)
        return {str(key): _jsonable(item) for key, item in mapped.items()}
    if isinstance(value, tuple | list):
        sequence = cast(tuple[object, ...] | list[object], value)
        return [_jsonable(item) for item in sequence]
    return value
