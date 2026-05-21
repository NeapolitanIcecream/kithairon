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
| `experiments/` | Persists polish experiments and builds the run-local catalog that merges base candidates with saved variants. |
| `polish/` | Runs selected-bar local polish and fixed-voice bounded multi-edit pitch search. |
| `feedback/` | Translates plain-language feedback into deterministic polish requests. |
| `export.py` | Writes MIDI and MusicXML candidate outputs. |
| `pipeline.py` | Orchestrates a complete CLI or API generation run. |
| `visualization/` | Builds browser-facing data and artifact indexes. |
| `api/` | Serves the visualization API and optional built frontend. |

## Engine Flow

The `strict` engine enumerates exact transforms and scores each candidate. This is the baseline path, and strict candidates record `strict_canon: true`.

The `repair` engine starts from strict candidates and edits a limited number of follower notes when that improves the score. Repair candidates record the source strict candidate and edit plan.

The `solver` engine uses OR-Tools CP-SAT to search for a relaxed follower voice under edit limits. It keeps objective cost calculation in `engines/solver_objective.py` so pitch options and weights can be tested separately from CP-SAT model construction.

The `auto` engine ranks strict candidates first, then adds repair or solver candidates only when the configured quality thresholds call for them.

## Composition Assist Flow

Composition assist starts from the browser-facing candidate DTOs in `visualization.json`.
`polish/run_io.py` resolves the requested candidate through the run-local catalog instead of
only reading base run candidates. The catalog includes:

- base candidates from `visualization.json`
- persisted experiment variants from `experiments/*/experiment.json`
- provenance metadata: `source_kind`, `source_experiment_id`, and `parent_candidate_id`

That read path lets a saved experiment variant behave like any other candidate after reload.
The API can polish it again, translate feedback against it, return it through the candidate
endpoint, and serve its artifacts through `artifact_index.json`.

Derived polish variants use request-scoped stable ids instead of `parent + rank`. That keeps
repeated polish requests against the same parent candidate addressable after reload and lets the
catalog, artifact index, and frontend candidate merge reject true duplicate ids instead of
silently aliasing them.

Fixed-voice invention is implemented as a specialized polish mode, not a separate generation
engine. It keeps the locked voice fixed, preserves rhythm and note count, and searches a bounded
set of pitch edits in the selected bars. Lower-voice search ranks variants with bass-support
analysis signals. Upper-voice search ranks variants with phrase, contour, and cadence signals.

Phrase analysis now carries per-warning provenance. Each phrase warning records the affected
voice role and concrete event ids, which lets the UI highlight the exact notes and map quick
actions to the intended rewrite target instead of always falling back to generic follower edits.

## Generated Artifacts

Each run writes:

- `results.json`: full candidate data, scores, violations, transforms, and output paths.
- `report.md`: readable candidate summary and penalty reasons.
- `resolved_config.toml`: the resolved config for the run.
- `visualization.json`: browser-facing run and candidate data.
- `artifact_index.json`: safe API download map for run and candidate artifacts.
- `candidates/*.musicxml` and `candidates/*.mid`: playable candidate exports.

The API never lets the browser read arbitrary local paths. Downloads go through `artifact_index.json`, and read-only API mode blocks uploads and render mutations.
