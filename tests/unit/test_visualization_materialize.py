from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

from kithairon.ir import CanonCandidate, Melody, NoteEvent, RuleViolation, TransformSpec, Voice
from kithairon.visualization.materialize import materialize_candidate


def test_materialize_candidate_makes_note_ids_unique_per_voice() -> None:
    candidate = _candidate(
        violations=(
            RuleViolation(
                rule_id="range",
                severity="hard",
                penalty=5,
                message="Out of range.",
                voice_ids=("follower",),
                event_ids=("n0001",),
            ),
        )
    )

    dto = materialize_candidate(candidate)

    assert [note.event_id for note in dto.notes] == ["leader:n0001", "follower:n0001"]
    assert dto.violations[0].event_ids == ["follower:n0001"]
    assert dto.violations[0].ir_event_ids == ["n0001"]


def test_materialize_candidate_derives_range_violation_position_from_event() -> None:
    candidate = _candidate(
        follower_events=(NoteEvent(id="n0001", pitch=95, start=Fraction(5), duration=Fraction(1)),),
        violations=(
            RuleViolation(
                rule_id="range",
                severity="hard",
                penalty=5,
                message="Out of range.",
                voice_ids=("follower",),
                event_ids=("n0001",),
            ),
        ),
    )

    violation = materialize_candidate(candidate).violations[0]

    assert violation.start_q is not None
    assert violation.start_q.text == "5"
    assert violation.end_q is not None
    assert violation.end_q.text == "6"
    assert violation.bar == 2
    assert violation.beat is not None
    assert violation.beat.text == "2"


def test_materialize_candidate_derives_large_leap_span_from_two_events() -> None:
    candidate = _candidate(
        follower_events=(
            NoteEvent(id="n0001", pitch=60, start=Fraction(0), duration=Fraction(1)),
            NoteEvent(id="n0002", pitch=79, start=Fraction(1), duration=Fraction(2)),
        ),
        violations=(
            RuleViolation(
                rule_id="large_leap",
                severity="soft",
                penalty=2,
                message="Large leap.",
                voice_ids=("follower",),
                event_ids=("n0001", "n0002"),
            ),
        ),
    )

    violation = materialize_candidate(candidate).violations[0]

    assert violation.start_q is not None
    assert violation.start_q.text == "0"
    assert violation.end_q is not None
    assert violation.end_q.text == "3"
    assert violation.category == "melody"


def test_materialize_repair_edit_plan_creates_repair_actions_and_origins() -> None:
    candidate = replace(
        _candidate(),
        engine="repair",
        strict_canon=False,
        metadata={
            "rank": 1,
            "outputs": {"musicxml": "candidates/001.musicxml"},
            "edit_plan": [
                {
                    "voice": "follower",
                    "event_id": "n0001",
                    "operation": "octave_shift",
                    "from_pitch": 60,
                    "to_pitch": 72,
                    "bar": None,
                    "beat": None,
                }
            ],
            "score_breakdown": {
                "penalties": [
                    {
                        "rule_id": "range",
                        "weighted_penalty": 4.5,
                    }
                ]
            },
        },
    )

    dto = materialize_candidate(candidate)

    assert dto.rank == 1
    assert dto.artifacts == {"musicxml": "candidates/001.musicxml"}
    assert dto.repair_actions[0].kind == "octave_displacement"
    assert dto.repair_actions[0].original_event_id == "follower:n0001"
    assert dto.repair_actions[0].bar == 1
    follower_note = next(note for note in dto.notes if note.event_id == "follower:n0001")
    assert follower_note.transform_origin == "repair"
    assert dto.score.by_rule == {"range": 4.5}
    assert dto.score.by_category == {"range": 4.5}


def test_materialize_solver_edit_plan_marks_solver_assignments() -> None:
    candidate = replace(
        _candidate(),
        engine="solver",
        strict_canon=False,
        metadata={
            "edit_plan": [
                {
                    "voice": "follower",
                    "event_id": "n0001",
                    "operation": "cp_sat_pitch_assignment",
                    "from_pitch": 67,
                    "to_pitch": 64,
                }
            ]
        },
    )

    dto = materialize_candidate(candidate)

    assert dto.repair_actions[0].kind == "solver_assignment"
    follower_note = next(note for note in dto.notes if note.event_id == "follower:n0001")
    assert follower_note.transform_origin == "solver"


def _candidate(
    *,
    follower_events: tuple[NoteEvent, ...] | None = None,
    violations: tuple[RuleViolation, ...] = (),
) -> CanonCandidate:
    leader = Voice(
        name="leader",
        role="leader",
        melody=Melody(
            events=(NoteEvent(id="n0001", pitch=60, start=Fraction(0), duration=Fraction(1)),),
            time_signature="4/4",
        ),
    )
    follower = Voice(
        name="follower",
        role="follower",
        melody=Melody(
            events=follower_events
            or (NoteEvent(id="n0001", pitch=67, start=Fraction(1), duration=Fraction(1)),),
            time_signature="4/4",
        ),
    )
    return CanonCandidate(
        id="strict_0001",
        voices=(leader, follower),
        transform_spec=TransformSpec(
            delay=Fraction(1),
            interval=7,
            transform_mode="transposition",
        ),
        engine="strict",
        strict_canon=True,
        score=95.0,
        violations=violations,
    )
