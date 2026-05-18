"""Command line interface for Kithairon."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal

import typer
from rich.console import Console

from kithairon import __version__
from kithairon.config import build_config_overrides, load_config, write_resolved_config
from kithairon.errors import KithaironError

console = Console()

app = typer.Typer(
    name="canonize",
    help="Generate playable and explainable canon variants from a monophonic melody.",
    no_args_is_help=True,
)
config_app = typer.Typer(help="Inspect and write resolved configuration.")
app.add_typer(config_app, name="config")


def _option(*param_decls: str, **kwargs: Any) -> object:
    return typer.Option(*param_decls, **kwargs)  # pyright: ignore[reportUnknownMemberType]


CONFIG_PATH_OPTION: object = _option(
    "--config",
    "-c",
    exists=True,
    dir_okay=False,
    help="TOML config file to load before CLI overrides.",
)
OUT_PATH_OPTION: object = _option(
    "--out",
    "-o",
    dir_okay=False,
    help="Write the resolved config to this path instead of stdout.",
)
FORMAT_OPTION: object = _option(
    "--format",
    help="Resolved config output format.",
)
CHORD_POLICY_OPTION: object = _option(
    "--chord-policy",
    help="Override input chord handling: error, top-note, or bottom-note.",
)
ENGINE_OPTION: object = _option(
    "--engine",
    help="Override generation engine: auto, strict, repair, or solver.",
)
TOP_K_OPTION: object = _option("--top-k", min=1)


@app.callback()
def root() -> None:
    """Generate playable and explainable canon variants from a monophonic melody."""


@app.command()
def version() -> None:
    """Show the installed Kithairon version."""
    console.print(__version__)


@config_app.command("resolve")
def resolve_config(
    config_path: Annotated[Path | None, CONFIG_PATH_OPTION] = None,
    out: Annotated[Path | None, OUT_PATH_OPTION] = None,
    output_format: Annotated[Literal["toml", "json"], FORMAT_OPTION] = "toml",
    chord_policy: Annotated[str | None, CHORD_POLICY_OPTION] = None,
    engine: Annotated[str | None, ENGINE_OPTION] = None,
    top_k: Annotated[int | None, TOP_K_OPTION] = None,
) -> None:
    """Load config defaults, apply overrides, and print or write the resolved config."""
    overrides = build_config_overrides(
        chord_policy=chord_policy,
        engine=engine,
        top_k=top_k,
    )
    try:
        config = load_config(config_path, overrides)
    except KithaironError as exc:
        console.print_json(data=exc.to_diagnostic())
        raise typer.Exit(code=1) from exc

    rendered = config.to_json() + "\n" if output_format == "json" else config.to_toml()

    if out is None:
        console.print(rendered, end="")
    elif output_format == "toml":
        write_resolved_config(config, out)
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8")


def main() -> None:
    """Run the canonize command line application."""
    app()
