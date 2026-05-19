# Kithairon

Kithairon turns a monophonic MIDI or MusicXML melody into playable two-voice canon candidates. It enumerates strict canon transforms, scores the results with explicit harmony and voice-leading rules, and can produce relaxed repair or CP-SAT solver candidates when strict results are weak.

Use the CLI:

```bash
uv run canonize validate examples/melodies/scale_c_major.musicxml
uv run canonize generate examples/melodies/scale_c_major.musicxml --out tmp/strict --engine strict
```

Each generation run writes:

- `results.json`
- `report.md`
- `resolved_config.toml`
- `visualization.json`
- `artifact_index.json`
- `candidates/*.musicxml`
- `candidates/*.mid`

## Supported Input

- MIDI: `.mid`, `.midi`
- MusicXML: `.musicxml`, `.xml`, `.mxl`

Inputs are monophonic by default. Chord input fails unless you set `--chord-policy top-note` or `--chord-policy bottom-note`.

## Engines

- `strict`: exact transform of the input melody, marked `canon_label: "strict canon"`.
- `repair`: local follower-note edits from a strict candidate, marked `canon_label: "relaxed canon"`.
- `solver`: optional OR-Tools CP-SAT relaxed candidate search.
- `auto`: strict first, then repair, and solver only when `[solver].enabled = true` and the dependency is installed.

See [Scoring And Rules](scoring-and-rules.md) for the rule weights, score profiles, and strict-versus-relaxed canon semantics.

See [Architecture](architecture.md) for the generation pipeline and [FAQ](faq.md) for common setup and output questions.

See the repository README for command examples and output details.
