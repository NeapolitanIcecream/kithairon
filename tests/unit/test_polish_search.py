from __future__ import annotations

from fractions import Fraction
from typing import cast

from kithairon.ir import CanonCandidate, Melody, NoteEvent, TransformSpec, Voice
from kithairon.polish.models import PolishRequest
from kithairon.polish.search import search_polish_variants
from kithairon.visualization.materialize import materialize_candidate


def test_selected_bar_search_only_changes_rewrite_voice_inside_selected_bars() -> None:
    parent = _candidate()
    original_events = parent.voices[1].melody.events
    request = PolishRequest(
        bar_start=2,
        bar_end=2,
        lock_voice="leader",
        rewrite_voice="auto",
        max_variants=3,
        objective_preset="reduce_repetition",
    )

    variants = search_polish_variants(parent, request)

    assert 0 < len(variants) <= 3
    assert parent.voices[1].melody.events == original_events
    variant = variants[0]
    assert variant.metadata["parent_candidate_id"] == "strict_0001"
    assert variant.metadata["edited_bars"] == [2]
    assert variant.metadata["rewrite_voice"] == "follower"
    assert _outside_bar_note_dumps(variant, bar=2) == _outside_bar_note_dumps(parent, bar=2)
    assert _voice_pitches(variant, role="leader") == _voice_pitches(parent, role="leader")
    assert _voice_pitches(variant, role="follower") != _voice_pitches(parent, role="follower")


def test_locked_follower_causes_auto_rewrite_to_edit_leader() -> None:
    parent = _candidate()
    request = PolishRequest(
        bar_start=1,
        bar_end=1,
        lock_voice="follower",
        rewrite_voice="auto",
        max_variants=2,
    )

    variants = search_polish_variants(parent, request)

    assert variants
    assert variants[0].metadata["rewrite_voice"] == "leader"
    assert _voice_pitches(variants[0], role="follower") == _voice_pitches(parent, role="follower")
    assert _voice_pitches(variants[0], role="leader") != _voice_pitches(parent, role="leader")


def test_search_returns_no_variants_when_requested_rewrite_voice_is_locked() -> None:
    parent = _candidate()
    request = PolishRequest(
        bar_start=1,
        bar_end=1,
        lock_voice="follower",
        rewrite_voice="follower",
        max_variants=2,
    )

    assert search_polish_variants(parent, request) == ()


def test_polish_ranking_is_stable_and_uses_musicality_for_reduce_repetition() -> None:
    parent = _candidate()
    request = PolishRequest(
        bar_start=2,
        bar_end=2,
        lock_voice="leader",
        rewrite_voice="follower",
        max_variants=3,
        objective_preset="reduce_repetition",
    )

    first = search_polish_variants(parent, request)
    second = search_polish_variants(parent, request)

    assert [candidate.id for candidate in first] == [candidate.id for candidate in second]
    objective = cast(dict[str, object], first[0].metadata["polish_objective"])
    musicality_total = cast(float, objective["musicality_total"])
    assert musicality_total >= 0
    follower_pitches = _voice_pitches(first[0], role="follower")
    assert follower_pitches[4] != follower_pitches[5]


def _outside_bar_note_dumps(candidate: CanonCandidate, *, bar: int) -> list[dict[str, object]]:
    return [
        note.model_dump(mode="json")
        for note in materialize_candidate(candidate).notes
        if note.bar != bar
    ]


def _voice_pitches(candidate: CanonCandidate, *, role: str) -> tuple[int | None, ...]:
    voice = next(voice for voice in candidate.voices if voice.role == role)
    return tuple(event.pitch for event in voice.melody.events)


def _candidate() -> CanonCandidate:
    leader = Voice(
        name="leader",
        role="leader",
        melody=Melody(
            events=tuple(
                NoteEvent(
                    id=f"l{index}",
                    pitch=pitch,
                    start=Fraction(index),
                    duration=Fraction(1),
                )
                for index, pitch in enumerate((60, 62, 64, 65, 67, 69, 71, 72))
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
                    pitch=pitch,
                    start=Fraction(index),
                    duration=Fraction(1),
                )
                for index, pitch in enumerate((48, 50, 52, 53, 55, 55, 57, 59))
            ),
            time_signature="4/4",
        ),
    )
    return CanonCandidate(
        id="strict_0001",
        voices=(leader, follower),
        transform_spec=TransformSpec(delay=Fraction(1), interval=-12),
        engine="strict",
        strict_canon=True,
        score=92.0,
        violations=(),
    )
