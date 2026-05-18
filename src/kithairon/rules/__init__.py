"""Rule engine and built-in contrapuntal checks."""

from kithairon.rules.base import Rule, default_rules, evaluate_rules
from kithairon.rules.cadence import CadenceStabilityRule
from kithairon.rules.consonance import (
    StrongBeatConsonanceRule,
    WeakBeatDissonanceRule,
    is_consonant,
)
from kithairon.rules.crossing import VoiceCrossingRule
from kithairon.rules.melodic import LargeLeapRule
from kithairon.rules.parallels import ParallelPerfectRule
from kithairon.rules.range import RangeRule

__all__ = [
    "CadenceStabilityRule",
    "LargeLeapRule",
    "ParallelPerfectRule",
    "RangeRule",
    "Rule",
    "StrongBeatConsonanceRule",
    "VoiceCrossingRule",
    "WeakBeatDissonanceRule",
    "default_rules",
    "evaluate_rules",
    "is_consonant",
]
