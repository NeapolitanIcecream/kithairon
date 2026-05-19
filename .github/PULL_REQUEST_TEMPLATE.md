## Summary

- 

## Checks

- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] `uv run pyright`
- [ ] `uv run pytest`
- [ ] `uv run pytest benchmarks/test_performance_budgets.py -q` when generation, solver, API, or scoring performance can change
- [ ] `bash scripts/build-docs.sh` when docs, README links, or MkDocs navigation change
- [ ] `cd web && pnpm lint && pnpm test && pnpm build` when the web UI changes

## Notes

- Relevant example melodies or benchmark observations:
- User-facing documentation updated:
