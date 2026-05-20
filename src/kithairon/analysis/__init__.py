"""Analysis helpers for timeline, vertical interval, and voice-leading views."""

from kithairon.analysis.bass import BassMotionLabel, BassSupportSummary, summarize_bass_support
from kithairon.analysis.cadence import (
    CadenceStrength,
    CadenceSummary,
    CadenceType,
    summarize_cadence,
    summarize_cadences,
)
from kithairon.analysis.composition import CompositionAnalysis, analyze_composition
from kithairon.analysis.context import AnalysisContext, analyze_candidate
from kithairon.analysis.phrasing import PhraseSpan, build_phrase_spans
from kithairon.analysis.timeline import (
    BeatStrength,
    TimeSignatureInfo,
    TimeSlice,
    build_time_slices,
    parse_time_signature,
)
from kithairon.analysis.verticality import Verticality, build_verticalities
from kithairon.analysis.voice_leading import (
    VoiceLeadingQuartetAnalysis,
    build_voice_leading_quartets,
)

__all__ = [
    "AnalysisContext",
    "BassMotionLabel",
    "BassSupportSummary",
    "BeatStrength",
    "CadenceStrength",
    "CadenceSummary",
    "CadenceType",
    "CompositionAnalysis",
    "PhraseSpan",
    "TimeSignatureInfo",
    "TimeSlice",
    "Verticality",
    "VoiceLeadingQuartetAnalysis",
    "analyze_candidate",
    "analyze_composition",
    "build_phrase_spans",
    "build_time_slices",
    "build_verticalities",
    "build_voice_leading_quartets",
    "parse_time_signature",
    "summarize_bass_support",
    "summarize_cadence",
    "summarize_cadences",
]
