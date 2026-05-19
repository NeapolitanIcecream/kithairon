"""Command line interface for Kithairon."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Literal, NoReturn

import typer
from click import UsageError, get_current_context
from rich.console import Console

from kithairon import __version__
from kithairon.adapters.music21_parse import parse_melody
from kithairon.config import build_config_overrides, load_config, write_resolved_config
from kithairon.errors import Diagnostic, KithaironError
from kithairon.pipeline import GenerationRun, run_generation

console = Console()
debug_traceback = False
overwrite_output = False

app = typer.Typer(
    name="canonize",
    help="Generate playable and explainable canon variants from a monophonic melody.",
    no_args_is_help=True,
)
config_app = typer.Typer(help="Inspect and write resolved configuration.")
app.add_typer(config_app, name="config")


@dataclass(frozen=True)
class GenerateCommandOptions:
    config_path: Path | None
    chord_policy: str | None
    engine: str | None
    top_k: int | None
    score_profile: str | None
    overwrite: bool


def _option(*param_decls: str, **kwargs: Any) -> object:
    return typer.Option(*param_decls, **kwargs)  # pyright: ignore[reportUnknownMemberType]


def _argument(**kwargs: Any) -> object:
    return typer.Argument(**kwargs)  # pyright: ignore[reportUnknownMemberType]


INPUT_PATH_ARGUMENT: object = _argument(
    help="MIDI or MusicXML melody file to parse.",
)
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
OUT_DIR_OPTION: object = _option(
    "--out",
    "-o",
    file_okay=False,
    help="Directory where generated artifacts will be written.",
)
FORMAT_OPTION: object = _option(
    "--format",
    help="Resolved config output format.",
)
CHORD_POLICY_OPTION: object = _option(
    "--chord-policy",
    help="Override input chord handling: error, top-note, or bottom-note.",
)
PART_POLICY_OPTION: object = _option(
    "--part-policy",
    help="Override part selection: first, highest-average-pitch, or explicit-index.",
)
PART_INDEX_OPTION: object = _option("--part-index", min=0)
ENGINE_OPTION: object = _option(
    "--engine",
    help="Override generation engine: auto, strict, repair, or solver.",
)
TOP_K_OPTION: object = _option("--top-k", min=1)
SCORE_PROFILE_OPTION: object = _option(
    "--score-profile",
    help="Override scoring profile: permissive, pop-lite, or renaissance-lite.",
)
DEBUG_OPTION: object = _option(
    "--debug",
    help="Show Python tracebacks instead of compact JSON diagnostics.",
)
OVERWRITE_OUTPUT_OPTION: object = _option(
    "--overwrite",
    help="Replace an existing output directory instead of creating a suffixed directory.",
)


@app.callback()
def root(
    debug: Annotated[bool, DEBUG_OPTION] = False,
    overwrite: Annotated[bool, OVERWRITE_OUTPUT_OPTION] = False,
) -> None:
    """Generate playable and explainable canon variants from a monophonic melody."""
    global debug_traceback, overwrite_output
    debug_traceback = debug
    overwrite_output = overwrite


@app.command()
def version() -> None:
    """Show the installed Kithairon version."""
    console.print(__version__)


@app.command()
def validate(
    input_path: Annotated[Path, INPUT_PATH_ARGUMENT],
    config_path: Annotated[Path | None, CONFIG_PATH_OPTION] = None,
    chord_policy: Annotated[str | None, CHORD_POLICY_OPTION] = None,
    part_policy: Annotated[str | None, PART_POLICY_OPTION] = None,
    part_index: Annotated[int | None, PART_INDEX_OPTION] = None,
) -> None:
    """Validate that an input file can be parsed as a monophonic melody."""
    overrides = build_config_overrides(
        chord_policy=chord_policy,
        part_policy=part_policy,
        part_index=part_index,
    )
    try:
        config = load_config(config_path, overrides)
        melody = parse_melody(input_path, config.input)
    except KithaironError as exc:
        _exit_project_error(exc)
    except Exception as exc:
        _exit_unexpected_error(exc)

    console.print_json(
        data={
            "status": "ok",
            "path": str(input_path),
            "events": len(melody.events),
            "time_signature": melody.time_signature,
            "tempo_bpm": melody.tempo_bpm,
            "key_hint": melody.key_hint,
        }
    )


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def generate(
    input_path: Annotated[Path, INPUT_PATH_ARGUMENT],
    out: Annotated[Path, OUT_DIR_OPTION],
    config_path: Annotated[Path | None, CONFIG_PATH_OPTION] = None,
    chord_policy: Annotated[str | None, CHORD_POLICY_OPTION] = None,
    engine: Annotated[str | None, ENGINE_OPTION] = None,
    top_k: Annotated[int | None, TOP_K_OPTION] = None,
    score_profile: Annotated[str | None, SCORE_PROFILE_OPTION] = None,
) -> None:
    """Generate strict canon candidates and write export/report artifacts."""
    payload = _run_generate_command(
        input_path=input_path,
        out=out,
        options=GenerateCommandOptions(
            config_path=config_path,
            chord_policy=chord_policy,
            engine=engine,
            top_k=top_k,
            score_profile=score_profile,
            overwrite=_generate_overwrite_flag(),
        ),
    )
    console.print_json(data=payload)


def _run_generate_command(
    *,
    input_path: Path,
    out: Path,
    options: GenerateCommandOptions,
) -> dict[str, object]:
    overrides = build_config_overrides(
        chord_policy=options.chord_policy,
        engine=options.engine,
        top_k=options.top_k,
        score_profile=options.score_profile,
    )
    try:
        config = load_config(options.config_path, overrides)
        generation = run_generation(input_path, out, config, overwrite_output=options.overwrite)
    except KithaironError as exc:
        _exit_project_error(exc)
    except Exception as exc:
        _exit_unexpected_error(exc)

    return _generation_success_payload(generation)


def _generate_overwrite_flag() -> bool:
    context = get_current_context(silent=True)
    extra_args = [] if context is None else list(context.args)
    overwrite = overwrite_output
    for arg in extra_args:
        if arg == "--overwrite":
            overwrite = True
        else:
            raise UsageError(f"Unsupported generate option or argument: {arg}")
    return overwrite


def _generation_success_payload(generation: GenerationRun) -> dict[str, object]:
    return {
        "status": "ok",
        "engine": generation.results["engine"],
        "out": str(generation.output_dir),
        "candidates": len(generation.candidates),
        "results": str(generation.results_path),
        "report": str(generation.report_path),
        "resolved_config": str(generation.resolved_config_path),
        "visualization": str(generation.visualization_path),
        "artifact_index": str(generation.artifact_index_path),
    }


@config_app.command("resolve")
def resolve_config(
    config_path: Annotated[Path | None, CONFIG_PATH_OPTION] = None,
    out: Annotated[Path | None, OUT_PATH_OPTION] = None,
    output_format: Annotated[Literal["toml", "json"], FORMAT_OPTION] = "toml",
    chord_policy: Annotated[str | None, CHORD_POLICY_OPTION] = None,
    engine: Annotated[str | None, ENGINE_OPTION] = None,
    top_k: Annotated[int | None, TOP_K_OPTION] = None,
    score_profile: Annotated[str | None, SCORE_PROFILE_OPTION] = None,
) -> None:
    """Load config defaults, apply overrides, and print or write the resolved config."""
    overrides = build_config_overrides(
        chord_policy=chord_policy,
        engine=engine,
        top_k=top_k,
        score_profile=score_profile,
    )
    try:
        config = load_config(config_path, overrides)
    except KithaironError as exc:
        _exit_project_error(exc)
    except Exception as exc:
        _exit_unexpected_error(exc)

    rendered = config.to_json() + "\n" if output_format == "json" else config.to_toml()

    if out is None:
        console.print(rendered, end="")
    elif output_format == "toml":
        write_resolved_config(config, out)
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8")


def _exit_project_error(exc: KithaironError) -> NoReturn:
    if debug_traceback:
        raise exc
    console.print_json(data=exc.to_diagnostic())
    raise typer.Exit(code=1) from exc


def _exit_unexpected_error(exc: Exception) -> NoReturn:
    if debug_traceback:
        raise exc
    console.print_json(
        data=Diagnostic(
            code="internal_error",
            message="An unexpected internal error occurred. Re-run with --debug for a traceback.",
            details={"error_type": type(exc).__name__, "error": str(exc)},
        ).to_dict()
    )
    raise typer.Exit(code=1) from exc


def main() -> None:
    """Run the canonize command line application."""
    app()
