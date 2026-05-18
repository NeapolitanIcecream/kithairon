"""Dump the visualization API OpenAPI schema."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from kithairon.api.app import create_app


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Dump Kithairon visualization OpenAPI schema.")
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Path where openapi.json is written.",
    )
    args = parser.parse_args(argv)

    out = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    schema = create_app().openapi()
    out.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
