# Changelog

All notable changes to Kithairon are recorded here.

## 0.1.0 - 2026-05-19

Initial public preview.

### Added

- `canonize` CLI for validating MIDI and MusicXML melody inputs.
- Strict canon generation through explicit transforms, delays, intervals, inversion, retrograde, augmentation, and diminution.
- Repair engine for limited follower-note edits when strict candidates score poorly.
- Optional CP-SAT solver engine behind the `solver` extra.
- Explainable rule scoring with penalty breakdowns and quality status metadata.
- MIDI, MusicXML, JSON, Markdown report, resolved config, visualization, and artifact-index outputs.
- FastAPI visualization API and frontend workflow for inspecting generated candidates.
- GitHub Actions CI for Python lint/type/test checks, frontend lint/test/e2e/build checks, and Cremona refactor audit.
- Benchmark-style example melodies for quickstart, chromatic, sparse, stepwise, folk-like, and negative test coverage.

### Fixed

- Read-only visualization API mode now blocks render mutations as well as uploads.
