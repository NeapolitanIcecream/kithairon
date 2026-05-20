from __future__ import annotations

from fractions import Fraction

from kithairon.feedback.models import FeedbackTranslateRequest
from kithairon.feedback.translate import translate_feedback
from kithairon.ir import CanonCandidate, Melody, NoteEvent, TransformSpec, Voice
from kithairon.visualization.materialize import materialize_candidate


def test_feedback_translation_maps_cadence_to_final_two_bar_action() -> None:
    candidate = materialize_candidate(_candidate())

    translation = translate_feedback(
        FeedbackTranslateRequest(text="cadence weak", candidate_id=candidate.candidate_id),
        candidate=candidate,
    )

    assert translation.intents == ["cadence_weak"]
    assert translation.target.bar_start == 3
    assert translation.target.bar_end == 4
    assert translation.actions[0].request.objective_preset == "strengthen_cadence"


def test_feedback_translation_maps_bass_static_to_follower_rewrite() -> None:
    candidate = materialize_candidate(_candidate())

    translation = translate_feedback(
        FeedbackTranslateRequest(
            text="bass too static in bars 1-2",
            candidate_id=candidate.candidate_id,
        ),
        candidate=candidate,
    )

    action = translation.actions[0]
    assert translation.intents == ["bass_too_static"]
    assert action.request.lock_voice == "leader"
    assert action.request.rewrite_voice == "follower"
    assert action.request.objective_preset == "smooth_bass"


def _candidate() -> CanonCandidate:
    leader = Voice(
        name="leader",
        role="leader",
        melody=Melody(
            events=tuple(
                NoteEvent(
                    id=f"l{index}",
                    pitch=60 + index,
                    start=Fraction(index),
                    duration=Fraction(1),
                )
                for index in range(16)
            ),
            time_signature="4/4",
        ),
    )
    follower = Voice(
        name="follower",
        role="follower",
        melody=Melody(
            events=tuple(
                NoteEvent(
                    id=f"f{index}",
                    pitch=48,
                    start=Fraction(index),
                    duration=Fraction(1),
                )
                for index in range(16)
            ),
            time_signature="4/4",
        ),
    )
    return CanonCandidate(
        id="strict_0001",
        voices=(leader, follower),
        transform_spec=TransformSpec(delay=Fraction(1)),
        engine="strict",
        strict_canon=True,
        score=80,
        violations=(),
    )
