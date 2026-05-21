"""Selected-bar pitch substitution search for local phrase polish."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import replace
from typing import cast

from kithairon.analysis.timeline import parse_time_signature
from kithairon.config import QualityConfig
from kithairon.ir import CanonCandidate, Voice, VoiceRole
from kithairon.polish.ids import derived_candidate_id
from kithairon.polish.models import PolishRequest
from kithairon.polish.objective import evaluate_objective
from kithairon.scoring import compute_musicality, score_candidate


def search_polish_variants(
    candidate: CanonCandidate,
    request: PolishRequest,
    *,
    score_profile: str = "pop-lite",
    quality: QualityConfig | None = None,
    request_token: str = "r001",
) -> tuple[CanonCandidate, ...]:
    """Return ranked local pitch-substitution variants without mutating the parent."""
    rewrite_role = _resolve_rewrite_role(request)
    if rewrite_role is None:
        return ()

    voice_index = _voice_index(candidate, rewrite_role)
    if voice_index is None:
        return ()

    voice = candidate.voices[voice_index]
    selected_indexes = _selected_event_indexes(voice, request)
    if not selected_indexes:
        return ()

    search_root = replace(
        candidate,
        metadata={
            **candidate.metadata,
            "polish_edit_plan": [],
        },
    )
    scored: list[tuple[CanonCandidate, float, int, int]] = []
    seen_pitch_sequences: set[tuple[int | None, ...]] = set()
    beam: list[CanonCandidate] = [search_root]
    serial = 0
    for _depth in range(_max_edited_notes(request)):
        wave: list[tuple[CanonCandidate, float, int, int]] = []
        for variant in _candidate_substitutions(beam, voice_index, selected_indexes, request):
            serial += 1
            scored_item = _scored_variant(
                parent=candidate,
                variant=variant,
                request=request,
                rewrite_role=rewrite_role,
                voice_index=voice_index,
                serial=serial,
                score_profile=score_profile,
                quality=quality,
                seen_pitch_sequences=seen_pitch_sequences,
            )
            if scored_item is None:
                continue
            scored.append(scored_item)
            wave.append(scored_item)
        if not wave:
            break
        beam = [item[0] for item in _rank_scored(wave)[: _beam_width(request)]]

    ranked = _rank_scored(scored)
    return tuple(
        _finalize_ranked_variant(
            parent_id=candidate.id,
            rank=rank,
            candidate=item[0],
            request_token=request_token,
        )
        for rank, item in enumerate(ranked[: request.max_variants], start=1)
    )


def _scored_variant(
    *,
    parent: CanonCandidate,
    variant: CanonCandidate,
    request: PolishRequest,
    rewrite_role: VoiceRole,
    voice_index: int,
    serial: int,
    score_profile: str,
    quality: QualityConfig | None,
    seen_pitch_sequences: set[tuple[int | None, ...]],
) -> tuple[CanonCandidate, float, int, int] | None:
    pitch_sequence = _voice_pitch_sequence(variant.voices[voice_index])
    if pitch_sequence in seen_pitch_sequences:
        return None
    seen_pitch_sequences.add(pitch_sequence)
    evaluated = score_candidate(variant, profile_name=score_profile, quality=quality)
    objective = evaluate_objective(
        evaluated,
        request,
        rewrite_role=rewrite_role,
        parent=parent,
    )
    musicality = compute_musicality(evaluated)
    ranking_score = musicality.total + objective.total
    hard_violations = sum(1 for violation in evaluated.violations if violation.severity == "hard")
    return (
        replace(
            evaluated,
            metadata={
                **evaluated.metadata,
                "parent_candidate_id": parent.id,
                "edited_bars": request.bar_range.as_list(),
                "rewrite_voice": rewrite_role,
                "search_mode": request.search_mode,
                "allow_rhythm_change": request.allow_rhythm_change,
                "polish_variant_serial": serial,
                "polish_objective": {
                    "preset": request.objective_preset,
                    "score": objective.total,
                    "components": dict(objective.components),
                    "weights": dict(objective.weights),
                    "musicality_total": musicality.total,
                    "ranking_score": round(ranking_score, 4),
                },
            },
        ),
        ranking_score,
        hard_violations,
        serial,
    )


def _rank_scored(
    scored: list[tuple[CanonCandidate, float, int, int]],
) -> list[tuple[CanonCandidate, float, int, int]]:
    return sorted(
        scored,
        key=lambda item: (item[2], -item[1], -item[0].score, item[3]),
    )


def _resolve_rewrite_role(request: PolishRequest) -> VoiceRole | None:
    if request.rewrite_voice != "auto":
        if request.lock_voice == request.rewrite_voice:
            return None
        return request.rewrite_voice
    if request.lock_voice == "follower":
        return "leader"
    return "follower"


def _voice_index(candidate: CanonCandidate, role: VoiceRole) -> int | None:
    for index, voice in enumerate(candidate.voices):
        if voice.role == role:
            return index
    return None


def _selected_event_indexes(voice: Voice, request: PolishRequest) -> tuple[int, ...]:
    meter = parse_time_signature(voice.melody.time_signature)
    indexes: list[int] = []
    for index, event in enumerate(voice.melody.events):
        if event.pitch is None:
            continue
        bar = int(event.start // meter.bar_length) + 1
        if request.bar_start <= bar <= request.bar_end:
            indexes.append(index)
    return tuple(indexes)


def _candidate_substitutions(
    beam: list[CanonCandidate],
    voice_index: int,
    selected_indexes: tuple[int, ...],
    request: PolishRequest,
) -> Iterable[CanonCandidate]:
    for candidate in beam:
        voice = candidate.voices[voice_index]
        edited_event_ids = _current_search_event_ids(candidate)
        for event_index in selected_indexes:
            event = voice.melody.events[event_index]
            if event.pitch is None or event.id in edited_event_ids:
                continue
            for delta in _pitch_deltas(request):
                next_pitch = event.pitch + delta
                if next_pitch < 0 or next_pitch > 127 or next_pitch == event.pitch:
                    continue
                yield _replace_voice_event_pitch(
                    candidate,
                    voice_index,
                    event_index,
                    next_pitch,
                    request,
                )


def _max_edited_notes(request: PolishRequest) -> int:
    if request.search_mode == "rewrite_selected_voice":
        return 3
    return 2


def _beam_width(request: PolishRequest) -> int:
    return max(8, request.max_variants * 3)


def _pitch_deltas(request: PolishRequest) -> tuple[int, ...]:
    if request.search_mode == "rewrite_selected_voice":
        return (-2, 2, -1, 1, -5, 5, -7, 7, -12, 12)
    if request.objective_preset == "smooth_bass":
        return (-2, 2, -1, 1, -5, 5, -7, 7)
    if request.objective_preset == "strengthen_cadence":
        return (-1, 1, -2, 2, -5, 5, -7, 7)
    return (-1, 1, -2, 2, -3, 3, -5, 5, -7, 7, -12, 12)


def _replace_voice_event_pitch(
    candidate: CanonCandidate,
    voice_index: int,
    event_index: int,
    pitch: int,
    request: PolishRequest,
) -> CanonCandidate:
    voice = candidate.voices[voice_index]
    events = list(voice.melody.events)
    original_event = events[event_index]
    events[event_index] = replace(original_event, pitch=pitch)
    melody = replace(voice.melody, events=tuple(events))
    voices = list(candidate.voices)
    voices[voice_index] = replace(voice, melody=melody)
    edit_action = {
        "voice": voice.role,
        "event_id": original_event.id,
        "operation": "pitch_replacement",
        "from_pitch": original_event.pitch,
        "to_pitch": pitch,
        "bar_range": request.bar_range.as_list(),
    }
    existing_plan = _metadata_actions(candidate.metadata.get("edit_plan"))
    current_plan = _metadata_actions(candidate.metadata.get("polish_edit_plan"))
    return replace(
        candidate,
        voices=cast(tuple[Voice, Voice], tuple(voices)),
        strict_canon=False,
        metadata={
            **candidate.metadata,
            "edit_plan": [*existing_plan, edit_action],
            "polish_edit_plan": [*current_plan, edit_action],
        },
    )


def _current_search_event_ids(candidate: CanonCandidate) -> set[str]:
    event_ids: set[str] = set()
    for action in _metadata_actions(candidate.metadata.get("polish_edit_plan")):
        event_id = action.get("event_id")
        if isinstance(event_id, str):
            event_ids.add(event_id)
    return event_ids


def _metadata_actions(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list | tuple):
        return []
    actions: list[dict[str, object]] = []
    items = cast(list[object] | tuple[object, ...], value)
    for item in items:
        if isinstance(item, Mapping):
            mapping = cast(Mapping[object, object], item)
            actions.append({str(key): raw_value for key, raw_value in mapping.items()})
    return actions


def _voice_pitch_sequence(voice: Voice) -> tuple[int | None, ...]:
    return tuple(event.pitch for event in voice.melody.events)


def _finalize_ranked_variant(
    *,
    parent_id: str,
    rank: int,
    candidate: CanonCandidate,
    request_token: str = "r001",
) -> CanonCandidate:
    return replace(
        candidate,
        id=derived_candidate_id(parent_id, request_token, rank),
        metadata={
            **candidate.metadata,
            "rank": rank,
            "polish_request_token": request_token,
        },
    )
