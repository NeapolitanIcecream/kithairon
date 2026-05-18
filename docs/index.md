# Kithairon

Kithairon is a symbolic music compiler for turning a monophonic melody into playable, explainable canon variants. The first implementation target is a two-voice canon pipeline that reads MIDI or MusicXML, creates strict canon candidates, scores them with explicit harmony and voice-leading rules, and later falls back to repair or solver engines when strict candidates are weak.

This repository is currently at the project skeleton stage. The package, CLI entry point, development tools, and documentation shell are in place; the music parsing and generation pipeline will be added in later implementation steps.

## Planned Input

- MIDI: `.mid`, `.midi`
- MusicXML: `.musicxml`, `.xml`, `.mxl`

The initial parser will expect a monophonic melody. Polyphonic input and chords will be rejected by default, with configurable policies planned for selecting the top or bottom note.

## Planned Output

Each generation run will write a directory containing a Markdown report, JSON results, the resolved configuration, and one MIDI plus one MusicXML file per exported candidate.

## Project Commands

```bash
uv run canonize --help
uv run pytest
uv run ruff check .
uv run pyright
```
