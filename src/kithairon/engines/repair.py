"""Beam-search repair engine for relaxed canon candidates."""

from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction

from kithairon.config import KithaironConfig, format_fraction
from kithairon.engines.strict import generate_strict_candidate_pool, transform_spec_to_dict
from kithairon.ir import CanonCandidate, Melody, NoteEvent, RuleViolation, Voice
from kithairon.rules.consonance import CONSONANT_SIMPLE_SEMITONES
from kithairon.scoring import quality_status, rank_candidates, score_candidate

EDIT_PENALTY = 1.5


@dataclass(frozen=True)
class EditAction:
    event_id: str
    operation: str
    from_pitch: int
    to_pitch: int
    reason: str
    bar: int | None
    beat: Fraction | None

    def to_dict(self) -> dict[str, object]:
        return {
            "voice": "follower",
            "event_id": self.event_id,
            "operation": self.operation,
            "from_pitch": self.from_pitch,
            "to_pitch": self.to_pitch,
            "delta": self.to_pitch - self.from_pitch,
            "reason": self.reason,
            "bar": self.bar,
            "beat": format_fraction(self.beat) if self.beat is not None else None,
        }


@dataclass(frozen=True)
class RepairState:
    follower: Melody
    edit_plan: tuple[EditAction, ...]
    candidate: CanonCandidate

    @property
    def edited_event_ids(self) -> frozenset[str]:
        return frozenset(action.event_id for action in self.edit_plan)


@dataclass(frozen=True)
class BeamRepairEngine:
    config: KithaironConfig

    def generate(self, melody: Melody) -> tuple[CanonCandidate, ...]:
        strict_pool = generate_strict_candidate_pool(melody, self.config)
        base_candidates = _select_base_candidates(strict_pool, self.config)
        repaired_candidates = tuple(
            candidate
            for index, base_candidate in enumerate(base_candidates, start=1)
            if (candidate := self._repair_base_candidate(base_candidate, index)) is not None
        )
        return rank_candidates(repaired_candidates, top_k=self.config.generation.top_k)

    def _repair_base_candidate(
        self,
        base_candidate: CanonCandidate,
        index: int,
    ) -> CanonCandidate | None:
        initial_state = _initial_repair_state(base_candidate, self.config, index)
        beam = (initial_state,)
        best_state = initial_state

        for _ in range(self.config.repair.max_steps):
            expanded_states = tuple(
                new_state
                for state in beam
                for new_state in _expand_state(state, base_candidate, self.config, index)
            )
            if not expanded_states:
                break

            beam = _top_beam_states(expanded_states, self.config.repair.beam_width)
            if beam[0].candidate.score > best_state.candidate.score:
                best_state = beam[0]

        if best_state.candidate.score <= base_candidate.score:
            return None
        return best_state.candidate


def generate_repair_candidates(
    melody: Melody,
    config: KithaironConfig,
) -> tuple[CanonCandidate, ...]:
    return BeamRepairEngine(config).generate(melody)


def _select_base_candidates(
    strict_pool: tuple[CanonCandidate, ...],
    config: KithaironConfig,
) -> tuple[CanonCandidate, ...]:
    repairable = tuple(candidate for candidate in strict_pool if _repairable_violations(candidate))
    low_scoring = tuple(
        candidate for candidate in repairable if candidate.score < config.quality.strict_good_score
    )
    candidate_pool = low_scoring or repairable
    return tuple(
        sorted(
            candidate_pool,
            key=lambda candidate: (-candidate.score, len(candidate.violations), candidate.id),
        )[: config.repair.beam_width]
    )


def _initial_repair_state(
    base_candidate: CanonCandidate,
    config: KithaironConfig,
    index: int,
) -> RepairState:
    follower = base_candidate.voices[1].melody
    candidate = _score_repair_candidate(
        base_candidate=base_candidate,
        follower=follower,
        edit_plan=(),
        config=config,
        index=index,
    )
    return RepairState(follower=follower, edit_plan=(), candidate=candidate)


def _expand_state(
    state: RepairState,
    base_candidate: CanonCandidate,
    config: KithaironConfig,
    index: int,
) -> tuple[RepairState, ...]:
    if _edit_limit_reached(state, config):
        return ()

    event_ids = _bad_follower_event_ids(state.candidate)
    actions = tuple(
        action
        for event_id in event_ids[: config.repair.beam_width]
        for action in _actions_for_event(state.candidate, event_id, state.edited_event_ids, config)
    )
    return tuple(
        _state_after_action(state, action, base_candidate, config, index) for action in actions
    )


def _state_after_action(
    state: RepairState,
    action: EditAction,
    base_candidate: CanonCandidate,
    config: KithaironConfig,
    index: int,
) -> RepairState:
    follower = _apply_action(state.follower, action)
    edit_plan = (*state.edit_plan, action)
    candidate = _score_repair_candidate(
        base_candidate=base_candidate,
        follower=follower,
        edit_plan=edit_plan,
        config=config,
        index=index,
    )
    return RepairState(follower=follower, edit_plan=edit_plan, candidate=candidate)


def _score_repair_candidate(
    *,
    base_candidate: CanonCandidate,
    follower: Melody,
    edit_plan: tuple[EditAction, ...],
    config: KithaironConfig,
    index: int,
) -> CanonCandidate:
    candidate = CanonCandidate(
        id=f"repair_{index:04d}_{base_candidate.id}",
        voices=(
            base_candidate.voices[0],
            Voice(name="follower", melody=follower, role="follower"),
        ),
        transform_spec=base_candidate.transform_spec,
        engine="repair",
        strict_canon=False,
        score=0.0,
        violations=(),
        metadata={
            "base_strict_candidate_id": base_candidate.id,
            "base_strict_score": base_candidate.score,
            "base_transform": transform_spec_to_dict(base_candidate.transform_spec),
            "bad_windows": _violation_summaries(base_candidate.violations),
            "edit_plan": [action.to_dict() for action in edit_plan],
        },
    )
    scored = score_candidate(candidate, quality=config.quality)
    edit_penalty = EDIT_PENALTY * len(edit_plan)
    adjusted_score = max(0.0, round(scored.score - edit_penalty, 2))
    return replace(
        scored,
        score=adjusted_score,
        metadata={
            **scored.metadata,
            "repair_edit_penalty": edit_penalty,
            "quality_status": quality_status(adjusted_score, config.quality),
        },
    )


def _repairable_violations(candidate: CanonCandidate) -> tuple[RuleViolation, ...]:
    follower_event_ids = _follower_event_ids(candidate)
    return tuple(
        violation
        for violation in candidate.violations
        if follower_event_ids.intersection(violation.event_ids)
    )


def _bad_follower_event_ids(candidate: CanonCandidate) -> tuple[str, ...]:
    follower_event_ids = _follower_event_ids(candidate)
    ordered_event_ids: list[str] = []
    for violation in sorted(candidate.violations, key=_violation_priority):
        for event_id in violation.event_ids:
            if event_id in follower_event_ids and event_id not in ordered_event_ids:
                ordered_event_ids.append(event_id)
    return tuple(ordered_event_ids)


def _actions_for_event(
    candidate: CanonCandidate,
    event_id: str,
    edited_event_ids: frozenset[str],
    config: KithaironConfig,
) -> tuple[EditAction, ...]:
    if event_id in edited_event_ids:
        return ()

    event = _event_by_id(candidate.voices[1].melody, event_id)
    if event is None or event.pitch is None:
        return ()

    violation = _violation_for_event(candidate, event_id)
    actions: list[EditAction] = []
    if config.repair.allow_pitch_replace:
        actions.extend(_nearest_consonance_actions(candidate, event, violation))
    if config.repair.allow_octave_shift:
        actions.extend(_octave_shift_actions(event, violation))
    return tuple(actions)


def _nearest_consonance_actions(
    candidate: CanonCandidate,
    event: NoteEvent,
    violation: RuleViolation,
) -> tuple[EditAction, ...]:
    assert event.pitch is not None
    leader_pitch = _active_pitch_at(candidate.voices[0].melody, event.start)
    if leader_pitch is None:
        return ()

    target_pitch = _nearest_consonant_pitch(event.pitch, leader_pitch)
    if target_pitch == event.pitch:
        return ()
    return (
        _edit_action(
            event=event,
            to_pitch=target_pitch,
            operation="nearest_consonance",
            violation=violation,
        ),
    )


def _octave_shift_actions(
    event: NoteEvent,
    violation: RuleViolation,
) -> tuple[EditAction, ...]:
    assert event.pitch is not None
    return tuple(
        _edit_action(
            event=event,
            to_pitch=event.pitch + octave_delta,
            operation="octave_shift",
            violation=violation,
        )
        for octave_delta in (-12, 12)
        if 21 <= event.pitch + octave_delta <= 108
    )


def _edit_action(
    *,
    event: NoteEvent,
    to_pitch: int,
    operation: str,
    violation: RuleViolation,
) -> EditAction:
    assert event.pitch is not None
    return EditAction(
        event_id=event.id,
        operation=operation,
        from_pitch=event.pitch,
        to_pitch=to_pitch,
        reason=violation.rule_id,
        bar=violation.bar,
        beat=violation.beat,
    )


def _nearest_consonant_pitch(current_pitch: int, leader_pitch: int) -> int:
    candidates = tuple(
        pitch
        for pitch in range(current_pitch - 12, current_pitch + 13)
        if pitch != current_pitch and abs(pitch - leader_pitch) % 12 in CONSONANT_SIMPLE_SEMITONES
    )
    if not candidates:
        return current_pitch
    return min(
        candidates,
        key=lambda pitch: (abs(pitch - current_pitch), abs(pitch - leader_pitch)),
    )


def _apply_action(melody: Melody, action: EditAction) -> Melody:
    return replace(
        melody,
        events=tuple(
            replace(event, pitch=action.to_pitch) if event.id == action.event_id else event
            for event in melody.events
        ),
    )


def _active_pitch_at(melody: Melody, offset: Fraction) -> int | None:
    for event in melody.events:
        if event.pitch is not None and event.start <= offset < event.start + event.duration:
            return event.pitch
    return None


def _event_by_id(melody: Melody, event_id: str) -> NoteEvent | None:
    for event in melody.events:
        if event.id == event_id:
            return event
    return None


def _violation_for_event(candidate: CanonCandidate, event_id: str) -> RuleViolation:
    for violation in sorted(candidate.violations, key=_violation_priority):
        if event_id in violation.event_ids:
            return violation
    return candidate.violations[0]


def _violation_priority(violation: RuleViolation) -> tuple[int, float, str]:
    severity_rank = 0 if violation.severity == "hard" else 1
    return (severity_rank, -violation.penalty, violation.rule_id)


def _top_beam_states(
    states: tuple[RepairState, ...],
    beam_width: int,
) -> tuple[RepairState, ...]:
    return tuple(
        sorted(
            states,
            key=lambda state: (state.candidate.score, -len(state.edit_plan), state.candidate.id),
            reverse=True,
        )[:beam_width]
    )


def _edit_limit_reached(state: RepairState, config: KithaironConfig) -> bool:
    edited_count = len(state.edited_event_ids)
    follower_event_count = max(1, len(state.follower.events))
    return (
        edited_count >= config.repair.max_edited_notes
        or edited_count / follower_event_count >= config.repair.max_edited_ratio
    )


def _follower_event_ids(candidate: CanonCandidate) -> frozenset[str]:
    return frozenset(event.id for event in candidate.voices[1].melody.events)


def _violation_summaries(violations: tuple[RuleViolation, ...]) -> list[dict[str, object]]:
    return [
        {
            "rule_id": violation.rule_id,
            "severity": violation.severity,
            "penalty": violation.penalty,
            "bar": violation.bar,
            "beat": format_fraction(violation.beat) if violation.beat is not None else None,
            "event_ids": list(violation.event_ids),
        }
        for violation in violations
    ]
