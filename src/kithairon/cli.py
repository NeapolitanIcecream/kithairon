"""Command line interface for Kithairon."""

from __future__ import annotations

import typer
from rich.console import Console

from kithairon import __version__

console = Console()

app = typer.Typer(
    name="canonize",
    help="Generate playable and explainable canon variants from a monophonic melody.",
    no_args_is_help=True,
)


@app.callback()
def root() -> None:
    """Generate playable and explainable canon variants from a monophonic melody."""


@app.command()
def version() -> None:
    """Show the installed Kithairon version."""
    console.print(__version__)


def main() -> None:
    """Run the canonize command line application."""
    app()
