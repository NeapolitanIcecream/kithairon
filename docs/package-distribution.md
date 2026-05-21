# Package Distribution

Kithairon publishes the Python package under the `kithairon-canon` distribution name. The import package and command names remain unchanged:

```bash
uv tool install kithairon-canon
canonize --help
canonize-web --help
```

Do not publish this project to PyPI under the `kithairon` distribution name. That name is already occupied by an unrelated package.

## Release version

Publish package-index releases from a tagged commit. The package version in `pyproject.toml`, `src/kithairon/__init__.py`, and `CHANGELOG.md` must match the tag without the leading `v`.

For example, release `0.1.2` from tag `v0.1.2`.

## Local package checks

Run the package check before publishing:

```bash
bash scripts/check-package.sh --install
```

The script:

- removes stale files from `dist/`;
- builds the wheel and source distribution;
- runs `twine check` against the built files;
- verifies the archive names and license metadata;
- installs the wheel into a clean virtual environment;
- checks that `canonize --help` and `canonize-web --help` start.

## TestPyPI

Publish to TestPyPI first:

```bash
bash scripts/check-package.sh --install
UV_PUBLISH_TOKEN="$TEST_PYPI_TOKEN" \
  uv publish \
  --publish-url https://test.pypi.org/legacy/ \
  --check-url https://test.pypi.org/simple/kithairon-canon/
```

Then install the uploaded package into a clean environment:

```bash
python3 -m venv /tmp/kithairon-testpypi
/tmp/kithairon-testpypi/bin/python -m pip install --upgrade pip
/tmp/kithairon-testpypi/bin/python -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  kithairon-canon==0.1.2
/tmp/kithairon-testpypi/bin/canonize --help
```

Use `--extra-index-url https://pypi.org/simple/` because TestPyPI may not host third-party dependencies.

You can also publish from GitHub Actions. Add `TEST_PYPI_TOKEN` to the `testpypi` environment, open the `Publish Package` workflow, and choose `testpypi`.

## PyPI

Publish to PyPI only after the TestPyPI install succeeds:

```bash
bash scripts/check-package.sh --install
UV_PUBLISH_TOKEN="$PYPI_TOKEN" \
  uv publish \
  --check-url https://pypi.org/simple/kithairon-canon/
```

After upload, install from PyPI in a clean environment:

```bash
python3 -m venv /tmp/kithairon-pypi
/tmp/kithairon-pypi/bin/python -m pip install --upgrade pip
/tmp/kithairon-pypi/bin/python -m pip install kithairon-canon==0.1.2
/tmp/kithairon-pypi/bin/canonize --help
```

For GitHub Actions publishing, add `PYPI_TOKEN` to the `pypi` environment, open the `Publish Package` workflow, and choose `pypi`.

Treat package-index uploads as immutable release events. If a broken artifact is published, cut a new version instead of replacing files in place.
