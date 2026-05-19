# Development

Use `uv` to install dependencies and run project tools.

## Set Up

```bash
uv sync
```

Install OR-Tools when working on the solver engine:

```bash
uv sync --extra solver
```

Preview this documentation site:

```bash
uv run --extra docs mkdocs serve
```

Build the deployment artifact:

```bash
bash scripts/build-docs.sh
```

Cloudflare Pages deployment settings are documented in [Deployment](deployment.md).

## Quality Checks

Run the full local gate before handing off changes:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run coverage run -m pytest
uv run coverage report
uv run pytest benchmarks/test_performance_budgets.py -q
bash scripts/build-docs.sh
```

Refresh benchmark observations when scoring, solver, repair, or example melodies change:

```bash
uv run python benchmarks/benchmark_melodies.py
```

## Refactor Audit

Kithairon uses Cremona to keep structural refactoring pressure visible. The baseline is committed at `quality/refactor-baseline.json`, and GitHub Actions fails when the current scan regresses against that baseline.

Run the same gate locally:

```bash
uv run coverage run -m pytest -q
uv run coverage json -o coverage.json
uv run cremona scan --baseline quality/refactor-baseline.json --coverage-json coverage.json --fail-on-regression
```

Open `output/refactor-audit/report.md` when the gate fails. Refresh the baseline only after a real debt reduction or a Cremona baseline schema change:

```bash
uv run cremona scan --update-baseline
```

## Package Layout

```text
src/kithairon/
  adapters/
  analysis/
  engines/
  rules/
  scoring/
  transforms/
  cli.py
  config.py
  export.py
  ir.py
  pipeline.py
  report.py
tests/
  unit/
  property/
  integration/
  golden/
examples/
  melodies/
benchmarks/
  benchmark_melodies.py
  benchmark_results.json
CHANGELOG.md
CONTRIBUTING.md
quality/
  refactor-baseline.json
```

`examples/melodies/README.md` describes the melody fixtures used for quickstart and benchmark-style coverage.
