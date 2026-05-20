from __future__ import annotations

from fractions import Fraction

from kithairon.ir import CanonCandidate, Melody, NoteEvent, TransformSpec, Voice
from kithairon.polish.models import PolishRequest
from kithairon.polish.search import search_polish_variants


def test_fixed_voice_invention_rewrites_selected_voice_and_records_mode() -> None:
    parent = _candidate()
    request = PolishRequest(
        bar_start=1,
        bar_end=1,
        lock_voice="leader",
        rewrite_voice="follower",
        search_mode="rewrite_selected_voice",
        max_variants=2,
    )

    variants = search_polish_variants(parent, request)

    assert variants
    assert variants[0].metadata["search_mode"] == "rewrite_selected_voice"
    assert variants[0].metadata["allow_rhythm_change"] is False
    assert _voice_pitches(variants[0], role="leader") == _voice_pitches(parent, role="leader")
    assert _voice_pitches(variants[0], role="follower") != _voice_pitches(parent, role="follower")


def test_fixed_voice_invention_can_rewrite_upper_above_fixed_lower() -> None:
    parent = _candidate()
    request = PolishRequest(
        bar_start=1,
        bar_end=1,
        lock_voice="follower",
        rewrite_voice="leader",
        search_mode="rewrite_selected_voice",
        max_variants=2,
    )

    variants = search_polish_variants(parent, request)

    assert variants
    assert variants[0].metadata["search_mode"] == "rewrite_selected_voice"
    assert variants[0].metadata["rewrite_voice"] == "leader"
    assert _voice_pitches(variants[0], role="follower") == _voice_pitches(parent, role="follower")
    assert _voice_pitches(variants[0], role="leader") != _voice_pitches(parent, role="leader")


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
                for index, pitch in enumerate((60, 62, 64, 65))
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
                for index, pitch in enumerate((48, 50, 52, 53))
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
