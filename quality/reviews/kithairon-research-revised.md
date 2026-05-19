# Revised Kithairon External Review

Date: 2026-05-19

This document revises an external LLM blind-review memo against the current state of the repository. The review was recalibrated using the README, `docs/`, core Python source, API routes, tests, GitHub Actions configuration, repository metadata, and a targeted reproduction of the read-only render behavior.

This is not a full CI rerun or an aesthetic evaluation of generated music. It is best treated as a release-readiness and refactoring-backlog review.

## Revised Score

Reference score: **82 / 100**

The score is reasonable, but the explanation needs adjustment. Kithairon's engineering baseline is stronger than some parts of the original memo imply: current CI already runs Python lint/type/test checks, frontend lint/test/e2e/build checks, and the Cremona refactor audit. At the same time, the read-only render issue is a confirmed mutation bug and should reduce the engineering-maturity assessment.

| Area | Score | Revised assessment |
| --- | ---: | --- |
| Positioning and completeness | 17 / 20 | The project has a clear goal: turn a monophonic melody into strict and relaxed canon variants, then write MIDI, MusicXML, JSON, Markdown reports, resolved config, and visualization artifacts. The README is enough for engineering users to get started, but the landing experience still lacks a direct musical demo. |
| Technical implementation | 24 / 30 | The IR, transforms, rules, scoring, repair beam search, CP-SAT solver, export flow, and visualization artifacts form a real pipeline. The main deductions are the heuristic solver objective and the confirmed read-only render mutation. |
| Engineering | 19 / 20 | Python 3.12, `uv`, Ruff, Pyright, pytest, coverage, Cremona, and GitHub Actions are in place. CI already uses `pnpm/action-setup@v6`, Node 24, and Playwright E2E. |
| Test quality | 13 / 15 | Unit, integration, golden snapshot, property-based, and visualization example tests cover important paths. The missing pieces are a read-only render regression test and a more representative real-melody benchmark fixture set. |
| Documentation and usability | 5 / 8 | The README, development docs, and visualization docs explain basic use and deployment. The gaps are scoring/rules assumptions, architecture explanation, FAQ, suitable and unsuitable melody types, and a top-level demo. The README output list also needs to include `visualization.json` and `artifact_index.json`. |
| Product and open-source maturity | 4 / 7 | The repository is public, but GitHub description, topics, and releases are still empty. A CHANGELOG, contribution guide, and credible demo assets would make the project easier to trust and try. |

## Acceptability

The external review can be accepted as a useful release-readiness backlog, but it should not be treated as a fully authoritative quality judgment. It did not install dependencies, run the complete test suite, or audition generated outputs, so its claims about musical quality and runtime reliability are static inferences.

Accept directly:

- The README and project front page need a "30-second demo".
- Scoring and rule assumptions should be documented in one place.
- The read-only render endpoint writes artifacts and conflicts with read-only semantics.
- The project lacks a real-melody benchmark set.
- Open-source packaging is incomplete: release, CHANGELOG, description, topics, and contribution guidance are missing.

Reframe or downgrade:

- Concerns about incomplete CI should be downgraded. Current CI already includes `ruff`, `pyright`, `pytest`, frontend lint/test/e2e/build, and Cremona audit.
- The suggestion to modularize and configure the solver objective is a reasonable medium-term refactor, but it should not block the next release. The safer sequence is to add documentation, benchmark fixtures, and regression tests before deciding the objective abstraction boundary.
- Product and open-source maturity should not be conflated with core code quality. It affects adoption and trust, but it is not direct evidence about generation correctness.

## Confirmed Issues

### 1. Read-only render semantics are incomplete

The candidate render path in `src/kithairon/api/routes_artifacts.py` invokes MuseScore rendering and then updates `artifact_index.json`. The current entry point checks `settings.musescore_bin`, but it does not check `settings.read_only`.

Targeted reproduction:

- Create a run with a normal app instance.
- Start a read-only app against the same output root.
- Configure a fake MuseScore executable and call the render endpoint.
- The endpoint returns `200` and writes `renders/...pdf`.

The original memo described this as a suspected read-only gap. It should now be treated as a confirmed bug. The fix should add a read-only guard to the render path and a regression test asserting that read-only render returns a `read_only_mode` error without writing render output or updating the artifact index.

### 2. README demo and output list are incomplete

The current README explains installation, quickstart, engine examples, strict and relaxed canons, input formats, config, errors, and the development gate. It still lacks a direct first-visit demo:

- An input melody.
- A generated score screenshot.
- A MIDI or audio demo.
- A web visualization screenshot or short gif.

The quickstart output directory list currently names `results.json`, `report.md`, `resolved_config.toml`, `candidates/*.musicxml`, and `candidates/*.mid`. The current pipeline also writes `visualization.json` and `artifact_index.json`, so the README should be updated.

### 3. Scoring and rules documentation is missing

The code already expresses clear musical assumptions, including:

- Consonant interval sets.
- The distinction between strict and relaxed canons.
- Strong-beat, parallel-perfect, cadence, and other rule penalties.
- Score profiles such as `permissive`, `pop-lite`, and `renaissance-lite`.

These assumptions are scattered across code and tests. External users cannot quickly tell:

- Which rules are hard constraints and which are soft preferences.
- How weights affect candidate ranking.
- Which style each score profile targets.
- Which melody types are likely to fail.
- Why a relaxed canon is still treated as a canon variant.

Add `docs/scoring-and-rules.md` and link it from the README.

### 4. Real-melody benchmarks are limited

`examples/melodies/` already contains basic examples and `bad_for_canon`, and visualization examples are covered by tests. It is still not a benchmark suite that represents product boundaries.

Recommended additions:

- Folk melody.
- Children's song.
- Stepwise diatonic melody.
- Chromatic melody.
- Rhythmically sparse melody.
- Negative example that is poor material for canon.

Each fixture should record the intended engine, typical output, human notes, and known failure modes. This set does not need to be a hard golden oracle at first, but it should become a repeatable observation suite for solver and scoring changes.

### 5. Open-source release metadata is incomplete

Current repository metadata remains sparse:

- Description is empty.
- Topics are empty.
- Latest release is empty.
- Stars and forks are both zero.

Stars and forks are not quality problems by themselves, but description, topics, release notes, CHANGELOG, and contribution guidance are part of a credible public release. Fill these before v0.1.0.

## Recommended Priority

P0:

- Fix the read-only render mutation bug.
- Add a read-only render regression test that proves render output and artifact index updates are blocked.

P1:

- Update the README quickstart output list to include `visualization.json` and `artifact_index.json`.
- Add a top-level 30-second demo with input, generated score, MIDI/audio, or a short gif.
- Add `docs/scoring-and-rules.md` covering scoring philosophy, hard and soft rules, profiles, and failure modes.

P2:

- Build a real-melody benchmark/examples set.
- Add GitHub description, topics, CHANGELOG, and contribution guidance.
- Publish a `v0.1.0` release.

P3:

- After benchmarks and documentation are stable, revisit solver objective modularization and configurability.
- Split solver objective constants, cadence preferences, pitch-option search, and edit weighting into clearer test units.

## Revised Core Recommendations

1. **Fix API read-only semantics first.** This is a confirmed behavior bug, not just documentation or packaging work.
2. **Make the README show the result faster.** The README is serviceable for engineering use, but it does not yet create a quick musical first impression.
3. **Document scoring and rules.** Users should understand Kithairon's rule preferences, style assumptions, and relaxed-canon boundary.
4. **Use real melody fixtures to constrain future refactors.** Establish repeatable examples before changing solver or scoring behavior.
5. **Complete the public-release wrapper.** Description, topics, CHANGELOG, release notes, and contribution guidance will reduce the cost of trying the project.

## Final Judgment

The original review's direction is acceptable, but it needs to be aligned with current repository facts. Kithairon is not missing basic engineering safeguards; the current concerns are more specific: one confirmed API mutation bug, documentation clarity, demo presentation, real-sample validation, and release packaging.

Accept the review as a prioritized improvement backlog, not as a set of equally urgent release blockers.
