"""Configuration models, loading, and resolved-config rendering."""

from __future__ import annotations

import json
import tomllib
from collections.abc import Mapping, Sequence
from fractions import Fraction
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_serializer,
    field_validator,
)

from kithairon.errors import ConfigError

type ChordPolicy = Literal["error", "top_note", "bottom_note"]
type PartPolicy = Literal["first", "highest_average_pitch", "explicit_index"]
type GenerationEngine = Literal["auto", "strict", "repair", "solver"]
type TransformName = Literal[
    "identity",
    "transposition",
    "inversion",
    "retrograde",
    "augmentation",
    "diminution",
]


class ConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def normalize_cli_token(value: str) -> str:
    return value.replace("-", "_")


def parse_fraction(value: object) -> Fraction:
    if isinstance(value, Fraction):
        parsed = value
    elif isinstance(value, int):
        parsed = Fraction(value, 1)
    elif isinstance(value, float):
        parsed = Fraction(str(value))
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("fraction value cannot be empty")
        parsed = Fraction(text)
    else:
        raise TypeError(f"expected fraction-compatible value, got {type(value).__name__}")

    if parsed <= 0:
        raise ValueError("fraction value must be positive")
    return parsed


def format_fraction(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def _parse_fraction_sequence(value: object) -> tuple[Fraction, ...]:
    raw_items: list[object]
    if isinstance(value, str):
        raw_items = [item.strip() for item in value.split(",")]
    elif isinstance(value, Sequence):
        raw_items = list(cast(Sequence[object], value))
    else:
        raise TypeError("expected a sequence of fraction values")

    return tuple(parse_fraction(item) for item in raw_items)


class InputConfig(ConfigModel):
    chord_policy: ChordPolicy = "error"
    part_policy: PartPolicy = "first"
    part_index: int = Field(default=0, ge=0)
    quantize: bool = True
    max_denominator: int = Field(default=48, ge=1)

    @field_validator("chord_policy", "part_policy", mode="before")
    @classmethod
    def normalize_policy(cls, value: object) -> object:
        if isinstance(value, str):
            return normalize_cli_token(value)
        return value


class GenerationConfig(ConfigModel):
    engine: GenerationEngine = "auto"
    top_k: int = Field(default=8, ge=1)
    max_candidates: int = Field(default=5000, ge=1)
    delays: tuple[Fraction, ...] = (Fraction(1), Fraction(2), Fraction(4), Fraction(8))
    intervals: tuple[int, ...] = (0, 12, -12, 7, -7, 5, -5, 4, 3, -3, 9, -9)
    transforms: tuple[TransformName, ...] = (
        "identity",
        "transposition",
        "inversion",
        "retrograde",
        "augmentation",
        "diminution",
    )
    rhythm_scales: tuple[Fraction, ...] = (Fraction(1), Fraction(2), Fraction(1, 2))

    @field_validator("engine", mode="before")
    @classmethod
    def normalize_engine(cls, value: object) -> object:
        if isinstance(value, str):
            return normalize_cli_token(value)
        return value

    @field_validator("transforms", mode="before")
    @classmethod
    def normalize_transforms(cls, value: object) -> object:
        if isinstance(value, str):
            return tuple(normalize_cli_token(item.strip()) for item in value.split(","))
        if isinstance(value, Sequence):
            normalized: list[object] = []
            for item in cast(Sequence[object], value):
                normalized.append(normalize_cli_token(item) if isinstance(item, str) else item)
            return tuple(normalized)
        return value

    @field_validator("intervals", mode="before")
    @classmethod
    def parse_intervals(cls, value: object) -> object:
        if isinstance(value, str):
            return tuple(int(item.strip()) for item in value.split(",") if item.strip())
        return value

    @field_validator("delays", "rhythm_scales", mode="before")
    @classmethod
    def parse_fraction_fields(cls, value: object) -> tuple[Fraction, ...]:
        return _parse_fraction_sequence(value)

    @field_serializer("delays", "rhythm_scales")
    def serialize_fraction_fields(self, values: tuple[Fraction, ...]) -> tuple[str, ...]:
        return tuple(format_fraction(value) for value in values)


class QualityConfig(ConfigModel):
    strict_good_score: int = Field(default=80, ge=0, le=100)
    strict_min_acceptable_score: int = Field(default=65, ge=0, le=100)
    auto_repair_threshold: int = Field(default=72, ge=0, le=100)
    auto_solver_threshold: int = Field(default=68, ge=0, le=100)


class RepairConfig(ConfigModel):
    beam_width: int = Field(default=24, ge=1)
    max_steps: int = Field(default=32, ge=0)
    max_edited_notes: int = Field(default=4, ge=0)
    max_edited_ratio: float = Field(default=0.2, ge=0.0, le=1.0)
    allow_pitch_replace: bool = True
    allow_octave_shift: bool = True
    allow_rhythm_edit: bool = False


class SolverConfig(ConfigModel):
    enabled: bool = False
    max_seconds: float = Field(default=3.0, gt=0.0)
    max_edited_notes: int = Field(default=4, ge=0)
    max_candidates_in: int = Field(default=8, ge=1)


class KithaironConfig(ConfigModel):
    input: InputConfig = Field(default_factory=InputConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    quality: QualityConfig = Field(default_factory=QualityConfig)
    repair: RepairConfig = Field(default_factory=RepairConfig)
    solver: SolverConfig = Field(default_factory=SolverConfig)

    def to_json_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_json(self) -> str:
        return json.dumps(self.to_json_dict(), indent=2, sort_keys=True)

    def to_toml(self) -> str:
        return config_to_toml(self)


def load_config(
    config_path: Path | None = None, overrides: Mapping[str, object] | None = None
) -> KithaironConfig:
    data: dict[str, object] = {}
    if config_path is not None:
        data = load_config_data(config_path)
    if overrides:
        data = deep_merge(data, overrides)
    return validate_config(data, source=str(config_path) if config_path else "defaults")


def load_config_data(config_path: Path) -> dict[str, object]:
    try:
        with config_path.open("rb") as handle:
            loaded = tomllib.load(handle)
    except FileNotFoundError as exc:
        raise ConfigError(
            f"Configuration file not found: {config_path}",
            code="config_not_found",
            details={"path": str(config_path)},
        ) from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(
            f"Configuration file is not valid TOML: {config_path}",
            code="config_invalid_toml",
            details={"path": str(config_path), "error": str(exc)},
        ) from exc

    return dict(loaded)


def validate_config(data: Mapping[str, object], *, source: str) -> KithaironConfig:
    try:
        return KithaironConfig.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(
            f"Configuration is invalid: {source}",
            code="config_invalid",
            details={"source": source, "errors": exc.errors(include_url=False)},
        ) from exc


def deep_merge(base: Mapping[str, object], overrides: Mapping[str, object]) -> dict[str, object]:
    merged: dict[str, object] = dict(base)
    for key, value in overrides.items():
        existing = merged.get(key)
        if existing is not None and isinstance(existing, Mapping) and isinstance(value, Mapping):
            merged[key] = deep_merge(
                cast(Mapping[str, object], existing),
                cast(Mapping[str, object], value),
            )
        else:
            merged[key] = value
    return merged


def build_config_overrides(
    *,
    chord_policy: str | None = None,
    part_policy: str | None = None,
    part_index: int | None = None,
    engine: str | None = None,
    top_k: int | None = None,
    solver_enabled: bool | None = None,
) -> dict[str, object]:
    overrides: dict[str, object] = {}
    input_overrides: dict[str, object] = {}
    generation_overrides: dict[str, object] = {}
    solver_overrides: dict[str, object] = {}

    if chord_policy is not None:
        input_overrides["chord_policy"] = normalize_cli_token(chord_policy)
    if part_policy is not None:
        input_overrides["part_policy"] = normalize_cli_token(part_policy)
    if part_index is not None:
        input_overrides["part_index"] = part_index
    if engine is not None:
        generation_overrides["engine"] = normalize_cli_token(engine)
    if top_k is not None:
        generation_overrides["top_k"] = top_k
    if solver_enabled is not None:
        solver_overrides["enabled"] = solver_enabled

    if input_overrides:
        overrides["input"] = input_overrides
    if generation_overrides:
        overrides["generation"] = generation_overrides
    if solver_overrides:
        overrides["solver"] = solver_overrides
    return overrides


def write_resolved_config(config: KithaironConfig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(config.to_toml(), encoding="utf-8")


def config_to_toml(config: KithaironConfig) -> str:
    data = config.to_json_dict()
    lines: list[str] = []
    for section, values in data.items():
        if not isinstance(values, Mapping):
            continue
        section_values = cast(Mapping[str, Any], values)
        if lines:
            lines.append("")
        lines.append(f"[{section}]")
        for key, value in section_values.items():
            lines.append(f"{key} = {_to_toml_value(value)}")
    lines.append("")
    return "\n".join(lines)


def _to_toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        sequence = cast(Sequence[Any], value)
        return "[" + ", ".join(_to_toml_value(item) for item in sequence) + "]"
    if value is None:
        raise TypeError("TOML output does not support null values")
    raise TypeError(f"Unsupported TOML value type: {type(value).__name__}")
