# Kithairon

Kithairon is a small symbolic music compiler that turns a monophonic melody into several playable canon variants. It will use explicit canon transformations to guarantee strict canon candidates, then apply explainable harmony and voice-leading rules to score them. When strict candidates are weak, optional repair and CP-SAT solver engines can produce relaxed canon variants while preserving a clear link to the original melody.

The repository is currently initialized for the first implementation step: Python package metadata, `src/` layout, a Typer CLI entry point, Ruff, Pyright, pytest, and English documentation scaffolding.

## Requirements

- Python 3.12 or newer
- `uv`

## Install

```bash
uv sync
```

Install the optional solver dependencies when working on the future CP-SAT engine:

```bash
uv sync --extra solver
```

Install the optional documentation dependencies when previewing the docs site:

```bash
uv sync --extra docs
```

## Quickstart

Show the CLI help:

```bash
uv run canonize --help
```

Show the installed package version:

```bash
uv run canonize version
```

Generation commands such as `canonize generate` will be added after the melody IR, parser, transform, scoring, and export layers are implemented.

## Development

Run the standard quality checks:

```bash
uv run pytest
uv run ruff check .
uv run pyright
```

Run the Cremona refactor audit locally:

```bash
uv run coverage run -m pytest -q
uv run coverage json -o coverage.json
uv run cremona scan --baseline quality/refactor-baseline.json --coverage-json coverage.json --fail-on-regression
```

The committed baseline lives at `quality/refactor-baseline.json`. Refresh it only after structural debt is intentionally reduced or Cremona changes its baseline schema:

```bash
uv run cremona scan --update-baseline
```

Preview the English documentation site:

```bash
uv run --extra docs mkdocs serve
```

## Planned Scope

The first full version will support MIDI and MusicXML input, strict canon enumeration, relaxed repair candidates, optional OR-Tools CP-SAT fallback, Markdown reports, JSON results, and exported MIDI/MusicXML files for each candidate.
