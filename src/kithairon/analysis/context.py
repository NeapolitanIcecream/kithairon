"""Top-level analysis context for canon candidates."""

from __future__ import annotations

from dataclasses import dataclass

from kithairon.analysis.timeline import TimeSlice, build_time_slices
from kithairon.analysis.verticality import Verticality, build_verticalities
from kithairon.analysis.voice_leading import (
    VoiceLeadingQuartetAnalysis,
    build_voice_leading_quartets,
)
from kithairon.ir import CanonCandidate


@dataclass(frozen=True)
class AnalysisContext:
    candidate: CanonCandidate
    time_slices: tuple[TimeSlice, ...]
    verticalities: tuple[Verticality, ...]
    voice_leadings: tuple[VoiceLeadingQuartetAnalysis, ...]


def analyze_candidate(candidate: CanonCandidate) -> AnalysisContext:
    """Analyze a two-voice candidate into metric, vertical, and voice-leading views."""
    time_signature = candidate.voices[0].melody.time_signature
    time_slices = build_time_slices(candidate.voices, time_signature=time_signature)
    verticalities = build_verticalities(time_slices)
    return AnalysisContext(
        candidate=candidate,
        time_slices=time_slices,
        verticalities=verticalities,
        voice_leadings=build_voice_leading_quartets(verticalities),
    )
