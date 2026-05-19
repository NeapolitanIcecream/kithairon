# Contributing

Use this guide when preparing changes for Kithairon.

## Set Up

Install the default package and development tools:

```bash
uv sync --group dev --extra solver --extra visual
```

Install frontend dependencies when working on the web UI:

```bash
cd web
pnpm install --frozen-lockfile
```

## Before Opening A Pull Request

Run the Python quality gate from the repository root:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
```

Run the frontend gate when touching `web/`:

```bash
cd web
pnpm lint
pnpm test
pnpm exec playwright install --with-deps chromium
pnpm e2e
pnpm build
```

Run the refactor audit when changing shared Python structure:

```bash
uv run coverage run -m pytest -q
uv run coverage json -o coverage.json
uv run cremona scan --baseline quality/refactor-baseline.json --coverage-json coverage.json --fail-on-regression
```

## Tests

Add or update tests for behavior changes. Bug fixes should include a regression test that fails before the fix and passes after it.

Use the melody fixtures in `examples/melodies/` when changing parser, generation, scoring, export, or visualization behavior:

```bash
uv run pytest tests/integration/test_visualization_examples.py -q
```

## Documentation

Update the README or `docs/` when a user-facing command, output file, configuration option, scoring behavior, or API behavior changes.

Preview the documentation site with:

```bash
uv run --extra docs mkdocs serve
```

## Release Notes

Update `CHANGELOG.md` for user-visible changes. Keep entries concrete: command names, file names, API behavior, and compatibility notes are more useful than general summaries.
