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
```
