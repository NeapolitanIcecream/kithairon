# Development

Use `uv` to create the environment, install dependencies, and run project tools.

## Set Up

```bash
uv sync
```

Install optional solver dependencies when working on the CP-SAT engine:

```bash
uv sync --extra solver
```

Install optional documentation dependencies when previewing the documentation site:

```bash
uv run --extra docs mkdocs serve
```

## Quality Checks

Run these commands before handing off changes:

```bash
uv run canonize --help
uv run pytest
uv run ruff check .
uv run pyright
```

## Refactor Audit

Kithairon uses Cremona to keep structural refactoring pressure visible. The baseline is committed at `quality/refactor-baseline.json`, and GitHub Actions fails when the current scan regresses against that baseline.

Run the same gate locally:

```bash
uv run coverage run -m pytest -q
uv run coverage json -o coverage.json
uv run cremona scan --baseline quality/refactor-baseline.json --coverage-json coverage.json --fail-on-regression
```

Open `output/refactor-audit/report.md` first when the gate fails. Refresh the baseline only after a real debt reduction or a Cremona baseline schema change:

```bash
uv run cremona scan --update-baseline
```

## Package Layout

```text
src/kithairon/
  __init__.py
  cli.py
tests/
  test_cli.py
docs/
  index.md
  development.md
quality/
  refactor-baseline.json
```
