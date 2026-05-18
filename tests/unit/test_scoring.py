from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

from kithairon.ir import CanonCandidate, Melody, NoteEvent, TransformSpec, Voice
from kithairon.scoring import quality_status, rank_candidates, score_candidate


def _candidate(
    candidate_id: str,
    leader_pitches: tuple[int, ...],
    follower_pitches: tuple[int, ...],
    *,
    transform_spec: TransformSpec | None = None,
) -> CanonCandidate:
    leader = Melody(
        events=tuple(
            NoteEvent(
                id=f"{candidate_id}_l{index}",
                pitch=pitch,
                start=Fraction(index),
                duration=Fraction(1),
            )
            for index, pitch in enumerate(leader_pitches)
        ),
        time_signature="4/4",
    )
    follower = Melody(
        events=tuple(
            NoteEvent(
                id=f"{candidate_id}_f{index}",
                pitch=pitch,
                start=Fraction(index),
                duration=Fraction(1),
            )
            for index, pitch in enumerate(follower_pitches)
        ),
        time_signature="4/4",
    )
    return CanonCandidate(
        id=candidate_id,
        voices=(
            Voice(name="leader", melody=leader, role="leader"),
            Voice(name="follower", melody=follower, role="follower"),
        ),
        transform_spec=transform_spec or TransformSpec(delay=Fraction(0)),
        engine="strict",
        strict_canon=True,
        score=0.0,
        violations=(),
    )


def test_obviously_bad_candidate_scores_low() -> None:
    candidate = _candidate("bad", (60, 52, 76), (49, 64, 45))

    scored = score_candidate(candidate, profile_name="renaissance-lite")

    assert scored.score < 55
    assert {violation.rule_id for violation in scored.violations} >= {
        "strong_beat_consonance",
        "voice_crossing",
    }


def test_simple_octave_canon_scores_relatively_high_under_permissive_profile() -> None:
    candidate = _candidate("octave", (60, 62, 64), (48, 50, 52))

    scored = score_candidate(candidate, profile_name="permissive")

    assert scored.score >= 80
    assert scored.metadata["quality_status"] == "good"


def test_score_breakdown_exposes_main_penalty_reasons() -> None:
    candidate = _candidate("explain", (60, 62), (49, 55))

    scored = score_candidate(candidate)
    breakdown = scored.metadata["score_breakdown"]

    assert isinstance(breakdown, dict)
    assert breakdown["top_penalties"][0]["rule_id"] == "strong_beat_consonance"
    assert breakdown["top_penalties"][0]["weighted_penalty"] > 0


def test_rank_candidates_uses_score_then_diversity() -> None:
    shared_transform = TransformSpec(delay=Fraction(1), interval=12, transform_mode="transposition")
    duplicate = _candidate("duplicate", (60,), (48,), transform_spec=shared_transform)
    duplicate = replace(duplicate, score=95.0, metadata={"source": "duplicate"})
    diverse = _candidate(
        "diverse",
        (60,),
        (55,),
        transform_spec=TransformSpec(delay=Fraction(2), interval=7, transform_mode="transposition"),
    )
    diverse = replace(diverse, score=92.0)
    same_family = _candidate("same_family", (60,), (48,), transform_spec=shared_transform)
    same_family = replace(same_family, score=94.0)

    ranked = rank_candidates((duplicate, same_family, diverse), top_k=2, diversity_penalty=4.0)

    assert [candidate.id for candidate in ranked] == ["duplicate", "diverse"]


def test_quality_status_uses_strict_thresholds() -> None:
    assert quality_status(90) == "good"
    assert quality_status(70) == "acceptable"
    assert quality_status(60) == "needs_solver"
