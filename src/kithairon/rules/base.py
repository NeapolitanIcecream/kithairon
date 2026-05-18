"""Rule protocol and orchestration helpers."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Protocol

from kithairon.analysis import AnalysisContext
from kithairon.ir import CanonCandidate, RuleViolation


class Rule(Protocol):
    @property
    def rule_id(self) -> str:
        """Stable identifier used in diagnostics and score breakdowns."""
        ...

    def evaluate(
        self,
        candidate: CanonCandidate,
        context: AnalysisContext,
    ) -> tuple[RuleViolation, ...]:
        """Return all violations for a candidate analysis context."""
        ...


def evaluate_rules(
    candidate: CanonCandidate,
    context: AnalysisContext,
    rules: Sequence[Rule] | None = None,
) -> tuple[RuleViolation, ...]:
    selected_rules = tuple(default_rules() if rules is None else rules)
    return tuple(
        violation
        for rule in selected_rules
        for violation in rule.evaluate(candidate, context)
    )


def default_rules() -> Iterable[Rule]:
    from kithairon.rules.cadence import CadenceStabilityRule
    from kithairon.rules.consonance import StrongBeatConsonanceRule, WeakBeatDissonanceRule
    from kithairon.rules.crossing import VoiceCrossingRule
    from kithairon.rules.melodic import LargeLeapRule
    from kithairon.rules.parallels import ParallelPerfectRule
    from kithairon.rules.range import RangeRule

    return (
        StrongBeatConsonanceRule(),
        WeakBeatDissonanceRule(),
        ParallelPerfectRule(),
        VoiceCrossingRule(),
        RangeRule(),
        LargeLeapRule(),
        CadenceStabilityRule(),
    )
