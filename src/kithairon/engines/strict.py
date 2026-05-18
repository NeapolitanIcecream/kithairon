"""Strict canon generation engine."""

from __future__ import annotations

from dataclasses import dataclass

from kithairon.config import KithaironConfig, format_fraction
from kithairon.ir import CanonCandidate, Melody, TransformSpec, Voice
from kithairon.scoring import rank_candidates, score_candidate
from kithairon.transforms.apply import apply_transform
from kithairon.transforms.enumerate import enumerate_transform_specs


@dataclass(frozen=True)
class StrictEngine:
    config: KithaironConfig

    def generate(self, melody: Melody) -> tuple[CanonCandidate, ...]:
        scored_candidates = tuple(
            score_candidate(
                _candidate_from_transform(melody, spec, index),
                quality=self.config.quality,
            )
            for index, spec in enumerate(
                enumerate_transform_specs(self.config.generation),
                start=1,
            )
        )
        return rank_candidates(
            scored_candidates,
            top_k=self.config.generation.top_k,
        )


def generate_strict_candidates(
    melody: Melody,
    config: KithaironConfig,
) -> tuple[CanonCandidate, ...]:
    return StrictEngine(config).generate(melody)


def _candidate_from_transform(
    melody: Melody,
    spec: TransformSpec,
    index: int,
) -> CanonCandidate:
    follower_melody = apply_transform(melody, spec)
    return CanonCandidate(
        id=f"strict_{index:04d}",
        voices=(
            Voice(name="leader", melody=melody, role="leader"),
            Voice(name="follower", melody=follower_melody, role="follower"),
        ),
        transform_spec=spec,
        engine="strict",
        strict_canon=True,
        score=0.0,
        violations=(),
        metadata={
            "candidate_index": index,
            "transform": transform_spec_to_dict(spec),
        },
    )


def transform_spec_to_dict(spec: TransformSpec) -> dict[str, object]:
    return {
        "delay": format_fraction(spec.delay),
        "interval": spec.interval,
        "transpose_mode": spec.transpose_mode,
        "transform_mode": spec.transform_mode,
        "inversion_axis": spec.inversion_axis,
        "rhythm_scale": format_fraction(spec.rhythm_scale),
        "octave_displacement": spec.octave_displacement,
    }
