# Melody Examples

These fixtures are monophonic inputs used for demos, integration tests, and regression checks. Most are intentionally small so generated canon candidates remain easy to inspect; the Bach demo preview is longer so the README can show a more musical example.

The style labels describe test coverage, not source attribution. The benchmark-style melodies are original public-domain-style fixtures and should not be treated as quotations from protected songs.

| File | Coverage role | Notes |
| --- | --- | --- |
| `scale_c_major.musicxml` | Quickstart demo | Short diatonic fragment with a rest. |
| `scale_c_major.mid` | MIDI parser smoke test | MIDI version of the quickstart fragment. |
| `bach_wtc1_c_major_prelude_upper.musicxml` | README demo preview | Longer monophonic incipit derived from the public-domain BWV 846 entry shipped in the music21 corpus. |
| `bad_for_canon.musicxml` | Negative example | Input that tends to need repair or solver help. |
| `folk_like_period.musicxml` | Folk-like period | Balanced phrase with a clear return to the tonic. |
| `children_style_stepwise.musicxml` | Stepwise children's-song style | Narrow range and simple rhythm. |
| `chromatic_turn.musicxml` | Chromatic stress case | Half-step motion that can create dissonant alignments. |
| `sparse_open_intervals.musicxml` | Sparse rhythm and leaps | Rests and open intervals that test delay alignment. |

When scoring or solver behavior changes, run the visualization example test to make sure every MusicXML fixture still generates artifacts:

```bash
uv run pytest tests/integration/test_visualization_examples.py -q
```
