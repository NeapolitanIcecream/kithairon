from __future__ import annotations

from fractions import Fraction

from kithairon.analysis.bass import summarize_bass_support
from kithairon.analysis.phrasing import build_phrase_spans
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


def test_fixed_voice_invention_can_return_multi_edit_variants() -> None:
    parent = _static_lower_candidate()
    request = PolishRequest(
        bar_start=1,
        bar_end=1,
        lock_voice="leader",
        rewrite_voice="follower",
        search_mode="rewrite_selected_voice",
        max_variants=8,
    )

    variants = search_polish_variants(parent, request)

    assert any(_changed_note_count(parent, variant, role="follower") > 1 for variant in variants)
    assert all(
        _voice_pitches(variant, role="leader") == _voice_pitches(parent, role="leader")
        for variant in variants
    )


def test_lower_fixed_voice_invention_prefers_improved_bass_support() -> None:
    parent = _weak_bass_support_candidate()
    parent_bass = summarize_bass_support(parent)
    request = PolishRequest(
        bar_start=1,
        bar_end=1,
        lock_voice="leader",
        rewrite_voice="follower",
        search_mode="rewrite_selected_voice",
        max_variants=4,
    )

    variants = search_polish_variants(parent, request)

    assert parent_bass is not None
    assert variants
    best_bass = summarize_bass_support(variants[0])
    assert best_bass is not None
    assert (
        best_bass.root_support_proxy > parent_bass.root_support_proxy
        or best_bass.sustained_foundation_score > parent_bass.sustained_foundation_score
        or best_bass.bass_independence_score > parent_bass.bass_independence_score
    )
    objective = variants[0].metadata["polish_objective"]
    assert isinstance(objective, dict)
    assert "bass_root_support_reward" in objective["components"]


def test_upper_fixed_voice_invention_prefers_reduced_phrase_warnings() -> None:
    parent = _plateau_upper_candidate()
    parent_warning_count = _phrase_warning_count(parent)
    request = PolishRequest(
        bar_start=1,
        bar_end=1,
        lock_voice="follower",
        rewrite_voice="leader",
        search_mode="rewrite_selected_voice",
        max_variants=4,
    )

    variants = search_polish_variants(parent, request)

    assert parent_warning_count > 0
    assert variants
    assert _phrase_warning_count(variants[0]) < parent_warning_count
    objective = variants[0].metadata["polish_objective"]
    assert isinstance(objective, dict)
    assert "phrase_warning_reduction_reward" in objective["components"]


def _voice_pitches(candidate: CanonCandidate, *, role: str) -> tuple[int | None, ...]:
    voice = next(voice for voice in candidate.voices if voice.role == role)
    return tuple(event.pitch for event in voice.melody.events)


def _changed_note_count(parent: CanonCandidate, variant: CanonCandidate, *, role: str) -> int:
    parent_pitches = _voice_pitches(parent, role=role)
    variant_pitches = _voice_pitches(variant, role=role)
    return sum(
        1 for before, after in zip(parent_pitches, variant_pitches, strict=True) if before != after
    )


def _phrase_warning_count(candidate: CanonCandidate) -> int:
    return sum(len(phrase.warnings) for phrase in build_phrase_spans(candidate))


def _candidate() -> CanonCandidate:
    return _candidate_with_pitches(
        leader_pitches=(60, 62, 64, 65),
        follower_pitches=(48, 50, 52, 53),
    )


def _static_lower_candidate() -> CanonCandidate:
    return _candidate_with_pitches(
        leader_pitches=(60, 62, 64, 65),
        follower_pitches=(48, 48, 48, 48),
    )


def _weak_bass_support_candidate() -> CanonCandidate:
    return _candidate_with_pitches(
        leader_pitches=(60, 64, 67, 72),
        follower_pitches=(49, 49, 49, 49),
    )


def _plateau_upper_candidate() -> CanonCandidate:
    return _candidate_with_pitches(
        leader_pitches=(60, 60, 60, 60),
        follower_pitches=(48, 50, 52, 53),
    )


def _candidate_with_pitches(
    *,
    leader_pitches: tuple[int, ...],
    follower_pitches: tuple[int, ...],
) -> CanonCandidate:
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
                for index, pitch in enumerate(leader_pitches)
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
                for index, pitch in enumerate(follower_pitches)
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
