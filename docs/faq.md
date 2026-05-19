# FAQ

## What input formats can I use?

Use MIDI (`.mid`, `.midi`) or MusicXML (`.musicxml`, `.xml`, `.mxl`).

## Does the input need to be monophonic?

Yes by default. Kithairon treats the input as one melody. If a MusicXML file contains chords and you want to extract one note from each chord, use `--chord-policy top-note` or `--chord-policy bottom-note`.

## What is the difference between strict and relaxed canon?

A strict canon keeps the follower voice as an exact transform of the input melody. A relaxed canon records the same transform lineage but may edit follower pitches under repair or solver limits.

## Why did my strict candidate score poorly?

Open `report.md` or inspect `visualization.json`. The score breakdown lists the strongest penalties, such as accented dissonance, parallel perfect intervals, voice crossing, large leaps, or weak cadence.

## When should I use the solver?

Use `--engine solver` when strict and repair candidates are too weak and you are willing to allow limited follower-note edits. Install the optional dependency first:

```bash
uv sync --extra solver
```

## Why does `auto` not always use the solver?

The solver is optional and is only used when `[solver].enabled = true`, the solver dependency is installed, and the strict or repair results fall below the configured quality thresholds.

## How do I get PDF, SVG, or PNG scores?

Install MuseScore CLI and start the visualization API with `--musescore-bin`:

```bash
uv run canonize-web --output-root ./runs --musescore-bin /path/to/musescore
```

Then use the render controls in the web UI. MIDI, MusicXML, report, results, and visualization downloads do not require MuseScore.

## What does read-only API mode do?

`canonize-web --read-only` serves existing runs without accepting uploads or render mutations. It is useful for browsing already generated runs without letting the server write new artifacts.

## Why did Kithairon write to `tmp/strict-1`?

If the requested output directory already exists and is not empty, Kithairon writes to a suffixed directory to avoid overwriting files. Put `--overwrite` before the subcommand when you want to replace the output directory.

```bash
uv run canonize --overwrite generate examples/melodies/scale_c_major.musicxml \
  --out tmp/strict \
  --engine strict
```
