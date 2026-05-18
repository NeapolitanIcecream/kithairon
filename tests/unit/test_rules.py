from __future__ import annotations

from fractions import Fraction

from kithairon.analysis import analyze_candidate
from kithairon.ir import CanonCandidate, Melody, NoteEvent, TransformSpec, Voice
from kithairon.rules import evaluate_rules
from kithairon.rules.consonance import StrongBeatConsonanceRule
from kithairon.rules.crossing import VoiceCrossingRule


def _candidate(
    leader_pitches: tuple[int, ...],
    follower_pitches: tuple[int, ...],
    *,
    duration: Fraction = Fraction(1),
) -> CanonCandidate:
    leader = Melody(
        events=tuple(
            NoteEvent(id=f"l{index}", pitch=pitch, start=index * duration, duration=duration)
            for index, pitch in enumerate(leader_pitches)
        ),
        time_signature="4/4",
    )
    follower = Melody(
        events=tuple(
            NoteEvent(id=f"f{index}", pitch=pitch, start=index * duration, duration=duration)
            for index, pitch in enumerate(follower_pitches)
        ),
        time_signature="4/4",
    )
    return CanonCandidate(
        id="rule_case",
        voices=(
            Voice(name="leader", melody=leader, role="leader"),
            Voice(name="follower", melody=follower, role="follower"),
        ),
        transform_spec=TransformSpec(delay=Fraction(0)),
        engine="strict",
        strict_canon=True,
        score=0.0,
        violations=(),
    )


def _rule_ids(candidate: CanonCandidate) -> set[str]:
    return {
        violation.rule_id for violation in evaluate_rules(candidate, analyze_candidate(candidate))
    }


def test_strong_beat_consonance_rule_catches_downbeat_dissonance() -> None:
    candidate = _candidate((60,), (49,))

    violations = StrongBeatConsonanceRule().evaluate(candidate, analyze_candidate(candidate))

    assert [violation.rule_id for violation in violations] == ["strong_beat_consonance"]
    assert violations[0].bar == 1
    assert violations[0].beat == 1
    assert violations[0].data["simple_semitones"] == 11


def test_parallel_perfect_rule_catches_parallel_fifths_and_octaves() -> None:
    parallel_fifth = _candidate((60, 62), (53, 55))
    parallel_octave = _candidate((60, 62), (48, 50))

    assert "parallel_perfect" in _rule_ids(parallel_fifth)
    assert "parallel_perfect" in _rule_ids(parallel_octave)


def test_voice_crossing_rule_catches_order_flip_between_voices() -> None:
    candidate = _candidate((60, 65), (64, 62))

    violations = VoiceCrossingRule().evaluate(candidate, analyze_candidate(candidate))

    assert [violation.rule_id for violation in violations] == ["voice_crossing"]
    assert violations[0].voice_ids == ("leader", "follower")


def test_evaluate_rules_returns_default_rule_violations() -> None:
    assert "strong_beat_consonance" in _rule_ids(_candidate((60,), (49,)))
    assert "parallel_perfect" in _rule_ids(_candidate((60, 62), (53, 55)))
