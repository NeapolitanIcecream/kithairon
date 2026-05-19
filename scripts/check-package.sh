#!/usr/bin/env bash
set -euo pipefail

install_check=false
if [[ "${1:-}" == "--install" ]]; then
  install_check=true
fi

rm -rf dist
uv build --no-sources
uvx twine check dist/*

uv run python - <<'PY'
from pathlib import Path
from tarfile import open as open_tar
from zipfile import ZipFile

dist = Path("dist")
wheels = sorted(dist.glob("kithairon_canon-*.whl"))
sdists = sorted(dist.glob("kithairon_canon-*.tar.gz"))
if len(wheels) != 1:
    raise SystemExit(f"expected one kithairon_canon wheel, found {len(wheels)}")
if len(sdists) != 1:
    raise SystemExit(f"expected one kithairon_canon sdist, found {len(sdists)}")

with ZipFile(wheels[0]) as wheel:
    wheel.testzip()
    names = set(wheel.namelist())
    if not any(".dist-info/" in name and name.endswith("LICENSE") for name in names):
        raise SystemExit("wheel is missing LICENSE metadata")

with open_tar(sdists[0], "r:gz") as sdist:
    for member in sdist.getmembers():
        if member.isfile():
            handle = sdist.extractfile(member)
            if handle is None:
                raise SystemExit(f"could not read sdist member: {member.name}")
            handle.read()
PY

if [[ "$install_check" == "true" ]]; then
  tmp_dir="$(mktemp -d)"
  trap 'rm -rf "$tmp_dir"' EXIT
  uv run python -m venv "$tmp_dir/venv"
  "$tmp_dir/venv/bin/python" -m pip install --upgrade pip
  "$tmp_dir/venv/bin/python" -m pip install dist/*.whl
  "$tmp_dir/venv/bin/canonize" --help >/dev/null
  "$tmp_dir/venv/bin/canonize-web" --help >/dev/null
fi
