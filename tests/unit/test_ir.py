from __future__ import annotations

from fractions import Fraction

from kithairon.ir import CanonCandidate, Melody, NoteEvent, RuleViolation, TransformSpec, Voice


def test_ir_models_represent_a_strict_two_voice_candidate() -> None:
    leader_melody = Melody(
        events=(
            NoteEvent(id="n0001", pitch=60, start=Fraction(0), duration=Fraction(1)),
            NoteEvent(id="n0002", pitch=None, start=Fraction(1), duration=Fraction(1, 2)),
        ),
        time_signature="4/4",
        tempo_bpm=120,
        key_hint="C major",
        source_path="examples/melodies/scale_c_major.musicxml",
    )
    follower_melody = Melody(
        events=(NoteEvent(id="n0001", pitch=72, start=Fraction(4), duration=Fraction(1)),),
        time_signature="4/4",
    )
    spec = TransformSpec(delay=Fraction(4), interval=12, transform_mode="transposition")

    candidate = CanonCandidate(
        id="strict_0001",
        voices=(
            Voice(name="leader", melody=leader_melody, role="leader"),
            Voice(name="follower", melody=follower_melody, role="follower"),
        ),
        transform_spec=spec,
        engine="strict",
        strict_canon=True,
        score=92.5,
        violations=(
            RuleViolation(
                rule_id="weak_dissonance",
                severity="soft",
                penalty=1.5,
                message="Weak-beat dissonance.",
                beat=Fraction(3, 2),
                event_ids=("n0002",),
            ),
        ),
    )

    assert candidate.voices[0].melody.events[1].pitch is None
    assert candidate.transform_spec.delay == Fraction(4)
    assert candidate.violations[0].beat == Fraction(3, 2)
