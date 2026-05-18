"""Markdown report rendering."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

from jinja2 import Template

REPORT_TEMPLATE = """# Kithairon Canon Report

Input: `{{ input_path }}`

Engine: `{{ engine }}`

Generated candidates: {{ candidates | length }}

## Top candidates

| Rank | ID | Score | Quality | Transform | Outputs |
| ---: | --- | ---: | --- | --- | --- |
{% for c in candidates -%}
| {{ c.r }} | `{{ c.id }}` | {{ "%.2f"|format(c.s) }} | {{ c.q }} | {{ c.t }} | {{ c.o }} |
{% endfor %}

## Main penalty reasons

{% for c in candidates -%}
### {{ c.r }}. `{{ c.id }}`
{% if c.p -%}
{% for penalty in c.p -%}
- `{{ penalty.rule_id }}`: {{ "%.2f"|format(penalty.weighted_penalty) }} - {{ penalty.message }}
{% endfor -%}
{% else -%}
- No penalties.
{% endif %}
{% if c.e %}
Edit plan:
{% for edit in c.e -%}
- `{{ edit.event_id }}` {{ edit.operation }}: {{ edit.from_pitch }} -> {{ edit.to_pitch }}
{% endfor -%}
{% endif %}

{% endfor -%}
"""


def render_report(results: Mapping[str, Any]) -> str:
    template = Template(REPORT_TEMPLATE)
    return template.render(**results)


def write_report(results: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(results), encoding="utf-8")


def report_candidate_rows(candidates: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [_report_candidate_row(candidate) for candidate in candidates]


def _report_candidate_row(candidate: Mapping[str, Any]) -> dict[str, Any]:
    transform = _mapping(candidate["transform_spec"])
    outputs = _mapping(candidate["outputs"])
    return {
        **dict(candidate),
        "r": candidate["rank"],
        "s": candidate["score"],
        "q": candidate["quality_status"],
        "t": _transform_summary(transform),
        "o": f"[MusicXML]({outputs['musicxml']}), [MIDI]({outputs['midi']})",
        "p": _top_penalties(candidate),
        "e": _edit_plan(candidate),
    }


def _top_penalties(candidate: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    score_breakdown = _mapping(candidate["score_breakdown"])
    top_penalties = score_breakdown.get("top_penalties", [])
    if not isinstance(top_penalties, list):
        return []
    return [_mapping(item) for item in cast(list[object], top_penalties)]


def _edit_plan(candidate: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    metadata = _mapping(candidate.get("metadata", {}))
    edit_plan = metadata.get("edit_plan", [])
    if not isinstance(edit_plan, list):
        return []
    return [_mapping(item) for item in cast(list[object], edit_plan)]


def _transform_summary(transform: Mapping[str, Any]) -> str:
    return (
        f"{transform['transform_mode']}, delay {transform['delay']}, "
        f"interval {transform['interval']}"
    )


def _mapping(value: object) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError("expected mapping value for report rendering")
    return cast(Mapping[str, Any], value)
