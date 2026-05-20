"""Selected-bar pitch substitution search for local phrase polish."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from typing import cast

from kithairon.analysis.timeline import parse_time_signature
from kithairon.config import QualityConfig
from kithairon.ir import CanonCandidate, Voice, VoiceRole
from kithairon.polish.models import PolishRequest
from kithairon.polish.objective import evaluate_objective
from kithairon.scoring import compute_musicality, score_candidate


def search_polish_variants(
    candidate: CanonCandidate,
    request: PolishRequest,
    *,
    score_profile: str = "pop-lite",
    quality: QualityConfig | None = None,
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

    scored: list[tuple[CanonCandidate, float, int, int]] = []
    seen_pitch_sequences: set[tuple[int | None, ...]] = set()
    for serial, variant in enumerate(
        _candidate_substitutions(candidate, voice_index, selected_indexes, request),
        start=1,
    ):
        pitch_sequence = _voice_pitch_sequence(variant.voices[voice_index])
        if pitch_sequence in seen_pitch_sequences:
            continue
        seen_pitch_sequences.add(pitch_sequence)
        evaluated = score_candidate(variant, profile_name=score_profile, quality=quality)
        objective = evaluate_objective(evaluated, request, rewrite_role=rewrite_role)
        musicality = compute_musicality(evaluated)
        ranking_score = musicality.total + objective.total
        hard_violations = sum(
            1 for violation in evaluated.violations if violation.severity == "hard"
        )
        scored.append(
            (
                replace(
                    evaluated,
                    metadata={
                        **evaluated.metadata,
                        "parent_candidate_id": candidate.id,
                        "edited_bars": request.bar_range.as_list(),
                        "rewrite_voice": rewrite_role,
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
        )

    ranked = sorted(
        scored,
        key=lambda item: (item[2], -item[1], -item[0].score, item[3]),
    )
    return tuple(
        _finalize_ranked_variant(parent_id=candidate.id, rank=rank, candidate=item[0])
        for rank, item in enumerate(ranked[: request.max_variants], start=1)
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
    candidate: CanonCandidate,
    voice_index: int,
    selected_indexes: tuple[int, ...],
    request: PolishRequest,
) -> Iterable[CanonCandidate]:
    voice = candidate.voices[voice_index]
    for event_index in selected_indexes:
        event = voice.melody.events[event_index]
        if event.pitch is None:
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


def _pitch_deltas(request: PolishRequest) -> tuple[int, ...]:
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
    return replace(
        candidate,
        voices=cast(tuple[Voice, Voice], tuple(voices)),
        strict_canon=False,
        metadata={
            **candidate.metadata,
            "edit_plan": [edit_action],
            "polish_edit_plan": [edit_action],
        },
    )


def _voice_pitch_sequence(voice: Voice) -> tuple[int | None, ...]:
    return tuple(event.pitch for event in voice.melody.events)


def _finalize_ranked_variant(
    *,
    parent_id: str,
    rank: int,
    candidate: CanonCandidate,
) -> CanonCandidate:
    return replace(
        candidate,
        id=f"{parent_id}_polish_{rank:03d}",
        metadata={
            **candidate.metadata,
            "rank": rank,
        },
    )
