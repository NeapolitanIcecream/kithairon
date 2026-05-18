"""Style profile weights for rule penalties."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from kithairon.ir import ViolationSeverity


def _default_rule_weights() -> Mapping[str, float]:
    return {}


@dataclass(frozen=True)
class StyleProfile:
    name: str
    rule_weights: Mapping[str, float] = field(default_factory=_default_rule_weights)
    severity_weights: Mapping[ViolationSeverity, float] = field(
        default_factory=lambda: {"hard": 1.35, "soft": 1.0, "info": 0.0}
    )
    default_rule_weight: float = 1.0

    def weight_for_rule(self, rule_id: str) -> float:
        return self.rule_weights.get(rule_id, self.default_rule_weight)

    def weight_for_severity(self, severity: ViolationSeverity) -> float:
        return self.severity_weights.get(severity, 1.0)


STYLE_PROFILES: Mapping[str, StyleProfile] = {
    "permissive": StyleProfile(
        name="permissive",
        rule_weights={
            "parallel_perfect": 0.30,
            "weak_beat_dissonance": 0.50,
            "large_leap": 0.65,
        },
        severity_weights={"hard": 1.15, "soft": 0.75, "info": 0.0},
    ),
    "pop-lite": StyleProfile(
        name="pop-lite",
        rule_weights={
            "strong_beat_consonance": 1.25,
            "parallel_perfect": 0.85,
            "voice_crossing": 1.10,
            "cadence_stability": 0.85,
        },
    ),
    "renaissance-lite": StyleProfile(
        name="renaissance-lite",
        rule_weights={
            "strong_beat_consonance": 1.55,
            "weak_beat_dissonance": 1.20,
            "parallel_perfect": 1.55,
            "voice_crossing": 1.35,
            "large_leap": 1.20,
            "cadence_stability": 1.15,
        },
        severity_weights={"hard": 1.45, "soft": 1.0, "info": 0.0},
    ),
}


def get_style_profile(profile_name: str) -> StyleProfile:
    try:
        return STYLE_PROFILES[profile_name]
    except KeyError as exc:
        known_profiles = ", ".join(sorted(STYLE_PROFILES))
        message = f"unknown scoring profile {profile_name!r}; expected {known_profiles}"
        raise ValueError(message) from exc
