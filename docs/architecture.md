# Architecture

This page gives a high-level map of the Kithairon generation pipeline.

## Pipeline

Kithairon keeps the pipeline explicit so each generated candidate can be traced back to the input melody and the rules that scored it.

```text
MIDI or MusicXML input
  -> music21 parser
  -> Kithairon melody IR
  -> strict transform pool
  -> analysis and rule evaluation
  -> score and ranking
  -> optional repair or solver candidates
  -> MIDI, MusicXML, JSON, report, and visualization artifacts
```

## Main Modules

| Module | Role |
| --- | --- |
| `adapters/` | Parses MIDI and MusicXML into the internal melody representation. |
| `ir.py` | Defines melody, note, voice, candidate, transform, and violation data models. |
| `transforms/` | Applies strict canon transforms such as transposition, inversion, retrograde, augmentation, and diminution. |
| `analysis/` | Builds vertical sonorities, beat strength, and voice-leading context. |
| `rules/` | Reports consonance, dissonance, parallel, crossing, range, leap, and cadence violations. |
| `scoring/` | Converts violations into weighted score breakdowns and ranks candidates. |
| `engines/` | Implements strict generation, repair search, and optional CP-SAT solver search. |
| `export.py` | Writes MIDI and MusicXML candidate outputs. |
| `pipeline.py` | Orchestrates a complete CLI or API generation run. |
| `visualization/` | Builds browser-facing data and artifact indexes. |
| `api/` | Serves the visualization API and optional built frontend. |

## Engine Flow

The `strict` engine enumerates exact transforms and scores each candidate. This is the baseline path, and strict candidates record `strict_canon: true`.

The `repair` engine starts from strict candidates and edits a limited number of follower notes when that improves the score. Repair candidates record the source strict candidate and edit plan.

The `solver` engine uses OR-Tools CP-SAT to search for a relaxed follower voice under edit limits. It keeps objective cost calculation in `engines/solver_objective.py` so pitch options and weights can be tested separately from CP-SAT model construction.

The `auto` engine ranks strict candidates first, then adds repair or solver candidates only when the configured quality thresholds call for them.

## Generated Artifacts

Each run writes:

- `results.json`: full candidate data, scores, violations, transforms, and output paths.
- `report.md`: readable candidate summary and penalty reasons.
- `resolved_config.toml`: the resolved config for the run.
- `visualization.json`: browser-facing run and candidate data.
- `artifact_index.json`: safe API download map for run and candidate artifacts.
- `candidates/*.musicxml` and `candidates/*.mid`: playable candidate exports.

The API never lets the browser read arbitrary local paths. Downloads go through `artifact_index.json`, and read-only API mode blocks uploads and render mutations.
