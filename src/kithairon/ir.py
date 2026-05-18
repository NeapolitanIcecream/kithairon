"""Core intermediate representation for symbolic melodies and candidates."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Literal

type Pitch = int
type VoiceName = str
type TieType = Literal["start", "continue", "stop"]
type VoiceRole = Literal["leader", "follower"]
type TransposeMode = Literal["chromatic", "diatonic"]
type TransformMode = Literal[
    "identity",
    "transposition",
    "inversion",
    "retrograde",
    "augmentation",
    "diminution",
]
type ViolationSeverity = Literal["hard", "soft", "info"]
type EngineName = Literal["strict", "repair", "solver"]


def _empty_metadata() -> Mapping[str, object]:
    return {}


@dataclass(frozen=True)
class NoteEvent:
    id: str
    pitch: Pitch | None
    start: Fraction
    duration: Fraction
    velocity: int = 64
    tie: TieType | None = None


@dataclass(frozen=True)
class Melody:
    events: tuple[NoteEvent, ...]
    time_signature: str
    tempo_bpm: int | None = None
    key_hint: str | None = None
    source_path: str | None = None


@dataclass(frozen=True)
class Voice:
    name: VoiceName
    melody: Melody
    role: VoiceRole


@dataclass(frozen=True)
class TransformSpec:
    delay: Fraction
    interval: int = 0
    transpose_mode: TransposeMode = "chromatic"
    transform_mode: TransformMode = "identity"
    inversion_axis: int | None = None
    rhythm_scale: Fraction = Fraction(1, 1)
    octave_displacement: int = 0


@dataclass(frozen=True)
class RuleViolation:
    rule_id: str
    severity: ViolationSeverity
    penalty: float
    message: str
    bar: int | None = None
    beat: Fraction | None = None
    voice_ids: tuple[str, ...] = ()
    event_ids: tuple[str, ...] = ()
    data: Mapping[str, object] = field(default_factory=_empty_metadata)


@dataclass(frozen=True)
class CanonCandidate:
    id: str
    voices: tuple[Voice, Voice]
    transform_spec: TransformSpec
    engine: EngineName
    strict_canon: bool
    score: float
    violations: tuple[RuleViolation, ...]
    metadata: Mapping[str, object] = field(default_factory=_empty_metadata)
