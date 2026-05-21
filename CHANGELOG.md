# Changelog

All notable changes to Kithairon are recorded here.

## 0.1.2 - 2026-05-21

Composition-assist and candidate-polish workflow expansion.

### Added

- Analysis-driven polish actions for phrase cadence, bass motion, fixed-voice invention, and follow-up variants.
- Candidate Lab experiment storage, saved-variant cataloging, and stable derived candidate identifiers.
- Compare view, feedback translation, musicality breakdowns, and phrase-polish controls in the web UI.
- API routes and generated OpenAPI schema updates for runs, artifacts, analysis, feedback, and polish workflows.
- Unit and integration coverage for analysis, feedback, polish search, experiment storage, CLI polish flows, and web components.

### Changed

- Improved config override structure and composition-assist documentation.

### Fixed

- Restored GitHub CI gates after workflow updates.
- Closed composition-assist audit gaps and stabilized CLI help assertions.

## 0.1.1 - 2026-05-19

Package-index release preparation.

### Added

- `kithairon-canon` distribution name for PyPI, while keeping the import package as `kithairon`.
- User-selectable scoring profiles across config, CLI, API upload handling, and the web upload panel.
- Package distribution documentation and local package verification script.
- Coverage and performance regression gates for release readiness.
- Security policy, code of conduct, issue templates, and pull request template.

### Changed

- Package metadata now includes README, SPDX license, license file, keywords, classifiers, and issue URL.

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
