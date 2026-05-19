# Package Distribution

Kithairon is currently distributed as source code and GitHub release artifacts. Do not publish this project to PyPI under the `kithairon` distribution name: that name is already occupied by an unrelated package.

## Current channel

Use GitHub releases for the public preview:

- Tag source releases from the `main` branch.
- Attach release notes that match `CHANGELOG.md`.
- Point users to the repository, hosted documentation, and `uv sync` install flow.

GitHub releases identify this repository and its source snapshots. They are not the same thing as package-index releases and do not reserve or claim a PyPI distribution name.

## Package-index plan

If Kithairon later needs a Python package-index release, choose a distinct distribution name such as `kithairon-canon`. The import package can remain `kithairon`; only the installable distribution name needs to change.

Before publishing to a package index:

1. Update `[project].name` to the chosen distribution name.
2. Build both wheel and source distributions.
3. Verify package metadata, license, README rendering, classifiers, and project URLs.
4. Publish to TestPyPI first and install into a clean environment.
5. Publish to PyPI only after the TestPyPI artifact installs and runs `canonize --help`.

Suggested local checks:

```bash
uv build
uv run python -m zipfile --test dist/*.whl
uv run python -m tarfile --test dist/*.tar.gz
```

Treat package-index uploads as immutable release events. If a broken artifact is published, cut a new version rather than replacing files in place.
