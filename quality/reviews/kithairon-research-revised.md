# Kithairon External Review, Current Repository State

Date: 2026-05-19

This document revises an external LLM review against the current repository
state. It keeps only the issues and improvement directions that remain valid
after checking the local source tree, documentation, tests, CI configuration,
GitHub repository metadata, the current GitHub release, and the PyPI project
namespace.

Targeted verification command:

```bash
uv run pytest tests/integration/test_api_artifacts.py \
  tests/integration/test_visualization_examples.py \
  tests/unit/test_config.py \
  tests/unit/test_scoring.py -q
```

Result: `21 passed`.

## Current Assessment

The original review is still useful as release-readiness backlog input, but
several of its concrete claims are now stale. The project now has a `v0.1.0`
GitHub release, GitHub description, homepage, topics, `CHANGELOG.md`,
`CONTRIBUTING.md`, README demo assets, scoring/rules documentation,
architecture and FAQ documentation, benchmark-style example melodies, and a
read-only render regression fix.

The remaining issues are more focused:

- scoring profiles exist in code and docs, but users cannot select them through
  config, CLI, or API controls;
- package metadata and external distribution strategy still need cleanup,
  especially because the PyPI name is already occupied by another project;
- example melodies are stronger now, but they are not yet a repeatable music
  quality evaluation suite;
- CI is broad, but it has no coverage floor or performance regression guard;
- visualization/API production boundaries are not documented clearly enough;
- repair and solver still duplicate some relaxed-candidate helper logic;
- governance and security files are still incomplete.

## Remaining Issues And Improvements

### 1. Expose scoring profiles to users

`src/kithairon/scoring/weights.py` defines `permissive`, `pop-lite`, and
`renaissance-lite`, and `docs/scoring-and-rules.md` explains them. However,
normal generation paths still call `score_candidate()` without passing a
profile, so CLI/API generation effectively uses the hard-coded default
`pop-lite`.

`KithaironConfig` has no `[scoring]` section, `canonize generate` has no
`--score-profile` option, and API upload overrides do not include a score
profile field. This makes the documented profiles look user-facing even though
they are still mainly internal and test-facing.

Recommended changes:

- add `ScoringConfig` with `profile = "pop-lite"`;
- validate profile names against `STYLE_PROFILES`;
- pass `config.scoring.profile` through strict, repair, solver, and auto
  scoring paths;
- add `--score-profile` to `generate` and `config resolve`;
- support score profile selection in API form/config JSON handling and Web UI
  controls;
- add tests proving that `renaissance-lite` and `permissive` change score
  breakdowns through the public generation path.

### 2. Finish package metadata and decide the PyPI distribution strategy

The repository now has a GitHub release, and `pyproject.toml` includes
Documentation and Repository URLs. As a distributable Python package, it still
lacks common metadata fields:

- `readme`;
- `license`;
- `classifiers`;
- `keywords`;
- an `Issues` URL.

There is also a distribution-name conflict: the `kithairon` name on PyPI is
already used by an unrelated Echo liquid handler package. This project should
not assume it can publish to PyPI under the `kithairon` distribution name.

Recommended changes:

- fill in the missing local package metadata;
- decide whether the short-term distribution plan is GitHub-only or a distinct
  package index name such as `kithairon-canon`;
- document the difference between GitHub releases and package-index releases;
- if package-index distribution is intended, add wheel/sdist build and metadata
  verification before publishing.

### 3. Turn example melodies into a repeatable evaluation suite

`examples/melodies/` now includes quickstart, Bach-derived demo, folk-like,
stepwise, chromatic, sparse, and negative fixtures. That resolves the original
"no real examples" concern in large part, but the examples are still not an
evaluation suite.

Current tests prove that each MusicXML fixture can generate visualization
artifacts. They do not record candidate counts, score distributions, runtime,
solver status, edit counts, listening notes, or human preference rankings. For
a symbolic music generator, this remains the main product-quality credibility
gap.

Recommended changes:

- add an `evaluation/` or `benchmarks/` directory;
- record strict, repair, solver, and auto outputs for representative fixtures
  where applicable;
- track candidate count, top score, quality status, runtime, solver status, and
  edit count;
- keep short listening notes for representative top candidates;
- add a lightweight script that refreshes `benchmark_results.json`;
- avoid turning human preference into a brittle unit-test oracle, but keep it
  visible when scoring changes.

### 4. Add coverage and performance regression guards

CI now includes Python lint/format/type/test, frontend lint/test/e2e/build, docs
build, and Cremona refactor audit. This is stronger than the original review
implied. The remaining gap is that CI does not enforce a coverage floor or
performance budget.

Current state:

- `coverage` is installed and used by the Cremona audit;
- there is no `coverage report --fail-under=...`;
- there is no `tests/performance/` or benchmark check;
- solver metadata records wall time and max time, but tests do not use that data
  as a regression constraint.

Recommended changes:

- measure the current baseline, then set a modest coverage fail-under;
- add performance tests or benchmark scripts for representative melodies;
- cover strict enumeration size, repair beam settings, solver timeout behavior,
  and API generation latency for small inputs;
- keep expensive benchmarks outside the default unit-test path if they are too
  costly for every pull request.

### 5. Document visualization/API production boundaries

The API already has important safety boundaries: upload suffix allowlisting, a
default 10 MiB upload limit, read-only mode, CORS allowlist configuration,
artifact-index path validation, and read-only render blocking. The remaining
gap is deployment documentation rather than a confirmed code bug.

`docs/visualization.md` explains development servers, production build serving,
and MuseScore rendering. It does not yet systematically cover:

- cleanup for uploads and `runs/_uploads`;
- disk quota expectations;
- concurrency limits;
- reverse-proxy request body limits;
- authentication expectations before exposing write endpoints;
- CORS configuration risks;
- where to place `--output-root` in production;
- whether public demos should run with `--read-only`.

Recommended changes:

- add a "Production notes" section to `docs/visualization.md`;
- recommend `--read-only` for public browsing of pre-generated runs;
- document cleanup and retention expectations for `runs/` and `_uploads/`;
- recommend body-size and rate limits at the reverse-proxy layer;
- state that upload/render endpoints should not be publicly exposed without an
  authentication or isolation plan.

### 6. Keep relaxed-candidate helper refactoring on the backlog

The solver objective has already been split into
`src/kithairon/engines/solver_objective.py`, so the original "modularize solver
objective" recommendation should be downgraded. The still-valid concern is that
repair and solver duplicate some related concepts:

- selecting strict bases that can be relaxed;
- identifying follower-related violations;
- summarizing violations into `bad_windows`;
- carrying base strict score and base transform metadata;
- representing edit-plan metadata.

This should not block current release work, but it is a reasonable maintenance
backlog item before adding rhythm repair, ornament repair, or more solver
objectives.

Recommended changes:

- wait until benchmark fixtures are stable, then extract a small
  `engines/relaxed_common.py`;
- keep the helper layer data-oriented and narrow;
- add regression tests for metadata shape before moving code.

### 7. Add remaining governance and security files

The repository now has `CHANGELOG.md`, `CONTRIBUTING.md`, Apache-2.0 license,
GitHub CI, release notes, and repository topics. It still lacks:

- `SECURITY.md`;
- `CODE_OF_CONDUCT.md`;
- `.github/ISSUE_TEMPLATE/`;
- `.github/PULL_REQUEST_TEMPLATE.md`.

`SECURITY.md` is the highest-priority item in this group because the project
includes a FastAPI upload/render surface, even if it is currently positioned as
a public preview.

Recommended changes:

- add a concise security policy with supported versions and vulnerability
  reporting path;
- add issue templates for bug reports, generation-quality reports, and docs
  issues;
- add a PR template that reminds contributors to run Python, frontend, docs, and
  relevant visualization/example checks.

## Priority Order

P0:

- expose scoring profile selection so config, CLI, and API behavior match the
  documentation;
- document API production deployment boundaries.

P1:

- finish package metadata and decide the package-index name strategy;
- add an example melody benchmark/evaluation directory.

P2:

- add coverage fail-under and performance regression checks;
- add `SECURITY.md` and GitHub issue/PR templates.

P3:

- refactor shared relaxed-candidate helper logic after benchmark coverage is
  strong enough to protect behavior.

## Revised Core Recommendation

Kithairon is now a credible `0.1.0` public preview; the remaining work is no
longer basic project setup. The most valuable next steps are to make documented
scoring controls real user-facing controls, make musical quality evaluation
repeatable, define the Python package distribution strategy, and document the
production boundaries of the visualization API.

## External Verification Sources

- GitHub release: <https://github.com/NeapolitanIcecream/kithairon/releases/tag/v0.1.0>
- PyPI `kithairon` project name: <https://pypi.org/project/kithairon/>
