"""Deterministic rule-based feedback translation."""

from __future__ import annotations

from kithairon.feedback.models import (
    FeedbackIntent,
    FeedbackTarget,
    FeedbackTranslateRequest,
    FeedbackTranslationDTO,
    SuggestedPolishAction,
)
from kithairon.polish.models import PolishObjectiveWeights, PolishRequest
from kithairon.visualization.models import CandidateVizDTO


def translate_feedback(
    request: FeedbackTranslateRequest,
    *,
    candidate: CandidateVizDTO | None = None,
) -> FeedbackTranslationDTO:
    intents = _detect_intents(request.text)
    target = _resolved_target(request.target, candidate, intents)
    action_intents: list[FeedbackIntent] = intents if intents else ["too_mechanical"]
    actions = [
        _action_for_intent(index, intent, target)
        for index, intent in enumerate(action_intents, start=1)
    ]
    return FeedbackTranslationDTO(
        input_text=request.text,
        candidate_id=request.candidate_id,
        intents=intents,
        target=target,
        actions=actions,
        explanation=_explanation(intents),
    )


def _detect_intents(text: str) -> list[FeedbackIntent]:
    normalized = text.lower()
    intents: list[FeedbackIntent] = []
    if any(token in normalized for token in ("mechanical", "robotic", "stiff", "机械")):
        intents.append("too_mechanical")
    if any(token in normalized for token in ("repetitive", "repeat", "same note", "重复")):
        intents.append("too_repetitive")
    if any(
        token in normalized
        for token in ("bass too static", "static bass", "bass static", "低音")
    ):
        intents.append("bass_too_static")
    if any(token in normalized for token in ("cadence weak", "weak cadence", "cadence", "终止")):
        intents.append("cadence_weak")
    if any(token in normalized for token in ("jumpy", "too many leaps", "leap", "跳")):
        intents.append("melody_too_jumpy")
    if any(
        token in normalized
        for token in ("rhythmically similar", "same rhythm", "rhythm too similar", "节奏")
    ):
        intents.append("voices_too_rhythmically_similar")
    return _dedupe(intents)


def _resolved_target(
    target: FeedbackTarget,
    candidate: CandidateVizDTO | None,
    intents: list[FeedbackIntent],
) -> FeedbackTarget:
    if target.bar_start is not None and target.bar_end is not None:
        return target
    final_bar = _final_bar(candidate)
    if "cadence_weak" in intents:
        return FeedbackTarget(bar_start=max(1, final_bar - 1), bar_end=final_bar)
    return FeedbackTarget(bar_start=target.bar_start or 1, bar_end=target.bar_end or final_bar)


def _action_for_intent(
    index: int,
    intent: FeedbackIntent,
    target: FeedbackTarget,
) -> SuggestedPolishAction:
    bar_start = target.bar_start or 1
    bar_end = target.bar_end or bar_start
    if intent == "too_repetitive":
        polish = PolishRequest(
            bar_start=bar_start,
            bar_end=bar_end,
            rewrite_voice="auto",
            objective_preset="reduce_repetition",
            objective_overrides=PolishObjectiveWeights(repeated_note_penalty=2.0),
        )
        label = "Reduce repeated notes"
    elif intent == "bass_too_static":
        polish = PolishRequest(
            bar_start=bar_start,
            bar_end=bar_end,
            lock_voice="leader",
            rewrite_voice="follower",
            objective_preset="smooth_bass",
            objective_overrides=PolishObjectiveWeights(bass_smoothness_penalty=2.5),
        )
        label = "Rewrite lower support"
    elif intent == "cadence_weak":
        polish = PolishRequest(
            bar_start=bar_start,
            bar_end=bar_end,
            rewrite_voice="auto",
            objective_preset="strengthen_cadence",
            objective_overrides=PolishObjectiveWeights(cadence_motion_reward=2.5),
        )
        label = "Strengthen cadence"
    elif intent == "melody_too_jumpy":
        polish = PolishRequest(
            bar_start=bar_start,
            bar_end=bar_end,
            rewrite_voice="auto",
            objective_preset="general_polish",
            objective_overrides=PolishObjectiveWeights(leap_penalty=2.4),
        )
        label = "Smooth melodic leaps"
    elif intent == "voices_too_rhythmically_similar":
        polish = PolishRequest(
            bar_start=bar_start,
            bar_end=bar_end,
            rewrite_voice="auto",
            objective_preset="general_polish",
            objective_overrides=PolishObjectiveWeights(repeated_note_penalty=1.2),
        )
        label = "Search a less parallel-feeling variant"
    else:
        polish = PolishRequest(
            bar_start=bar_start,
            bar_end=bar_end,
            rewrite_voice="auto",
            objective_preset="general_polish",
            objective_overrides=PolishObjectiveWeights(
                repeated_note_penalty=1.3,
                leap_penalty=1.2,
            ),
        )
        label = "General phrase polish"
    return SuggestedPolishAction(
        action_id=f"feedback-action-{index:02d}",
        label=label,
        reason=f"Mapped feedback intent {intent} to a deterministic polish request.",
        request=polish,
    )


def _final_bar(candidate: CandidateVizDTO | None) -> int:
    if candidate is None:
        return 1
    return max((note.bar for note in candidate.notes if note.bar is not None), default=1)


def _explanation(intents: list[FeedbackIntent]) -> str:
    if not intents:
        return "No specific intent was recognized, so a general polish action was suggested."
    return "Recognized feedback intents: " + ", ".join(intents)


def _dedupe(values: list[FeedbackIntent]) -> list[FeedbackIntent]:
    deduped: list[FeedbackIntent] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped
