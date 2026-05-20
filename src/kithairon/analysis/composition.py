"""Composition-assist analysis bundle."""

from __future__ import annotations

from dataclasses import dataclass

from kithairon.analysis.bass import BassSupportSummary, summarize_bass_support
from kithairon.analysis.cadence import CadenceSummary, summarize_cadence
from kithairon.analysis.context import analyze_candidate
from kithairon.analysis.phrasing import PhraseSpan, build_phrase_spans
from kithairon.ir import CanonCandidate


@dataclass(frozen=True)
class CompositionAnalysis:
    phrases: tuple[PhraseSpan, ...]
    cadence: CadenceSummary | None
    bass_support: BassSupportSummary | None


def analyze_composition(candidate: CanonCandidate) -> CompositionAnalysis:
    """Build the analysis bundle shown in composition-assist UI."""
    context = analyze_candidate(candidate)
    return CompositionAnalysis(
        phrases=build_phrase_spans(candidate),
        cadence=summarize_cadence(context),
        bass_support=summarize_bass_support(candidate),
    )
