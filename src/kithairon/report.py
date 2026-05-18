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
{% if fallback_path %}
## Fallback path

- reason: {{ fallback_path.reason }}
- strict best: {{ fallback_path.strict.best_score }}
- strict average: {{ fallback_path.strict.average_score }}
- repair: {% if fallback_path.repair.triggered %}triggered{% else %}skipped{% endif %}
- repair best: {{ fallback_path.repair.best_score }}
- solver: {% if fallback_path.solver.triggered %}triggered{% else %}skipped{% endif %}
- solver available: {{ fallback_path.solver.available }}
{% endif %}

## Top candidates

| Rank | ID | Canon | Score | Quality | Transform | Outputs |
| ---: | --- | --- | ---: | --- | --- | --- |
{% for c in candidates -%}
{{ c.row }}
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
{% if c.od %}
Objective details:
- status: `{{ c.od.status }}`
- objective: {{ c.od.objective_value }}
- wall time: {{ c.od.wall_time_seconds }}s
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
        "cl": candidate["canon_label"],
        "t": _transform_summary(transform),
        "o": f"[MusicXML]({outputs['musicxml']}), [MIDI]({outputs['midi']})",
        "row": _candidate_table_row(candidate, transform, outputs),
        "p": _top_penalties(candidate),
        "e": _edit_plan(candidate),
        "od": _objective_details(candidate),
    }


def _candidate_table_row(
    candidate: Mapping[str, Any],
    transform: Mapping[str, Any],
    outputs: Mapping[str, Any],
) -> str:
    score = float(candidate["score"])
    output_links = f"[MusicXML]({outputs['musicxml']}), [MIDI]({outputs['midi']})"
    return (
        f"| {candidate['rank']} | `{candidate['id']}` | {candidate['canon_label']} | "
        f"{score:.2f} | {candidate['quality_status']} | {_transform_summary(transform)} | "
        f"{output_links} |"
    )


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


def _objective_details(candidate: Mapping[str, Any]) -> Mapping[str, Any]:
    metadata = _mapping(candidate.get("metadata", {}))
    objective_details = metadata.get("objective_details", {})
    if not isinstance(objective_details, Mapping):
        return {}
    return cast(Mapping[str, Any], objective_details)


def _transform_summary(transform: Mapping[str, Any]) -> str:
    return (
        f"{transform['transform_mode']}, delay {transform['delay']}, "
        f"interval {transform['interval']}"
    )


def _mapping(value: object) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError("expected mapping value for report rendering")
    return cast(Mapping[str, Any], value)
