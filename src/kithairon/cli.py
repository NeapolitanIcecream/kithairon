"""Command line interface for Kithairon."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Literal, NoReturn

import typer
from click import UsageError, get_current_context
from pydantic import ValidationError
from rich.console import Console

from kithairon import __version__
from kithairon.adapters.music21_parse import parse_melody
from kithairon.config import (
    ConfigOverrideOptions,
    build_config_overrides,
    load_config,
    normalize_cli_token,
    write_resolved_config,
)
from kithairon.errors import Diagnostic, KithaironError
from kithairon.pipeline import GenerationRun, run_generation
from kithairon.polish import PolishRequest, polish_run_candidate

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


@dataclass(frozen=True)
class ExtraCommandOptions:
    chord_policy: str | None = None
    overwrite: bool = False
    score_profile: str | None = None


@dataclass(frozen=True)
class PolishCommandOptions:
    lock_voice: str = "none"
    rewrite_voice: str = "auto"
    preset: str = "general-polish"


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
CANDIDATE_ID_OPTION: object = _option(
    "--candidate",
    help="Candidate id to polish inside the run visualization.",
)
BARS_OPTION: object = _option(
    "--bars",
    help="Inclusive bar range to rewrite, for example 7-8 or 7.",
)
LOCK_VOICE_OPTION: object = _option(
    "--lock-voice",
    help="Voice to keep unchanged: leader, follower, or none.",
)
REWRITE_VOICE_OPTION: object = _option(
    "--rewrite-voice",
    help="Voice to rewrite: leader, follower, or auto.",
)
OBJECTIVE_PRESET_OPTION: object = _option(
    "--preset",
    help="Polish objective preset.",
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
        ConfigOverrideOptions(
            chord_policy=chord_policy,
            part_policy=part_policy,
            part_index=part_index,
        )
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
    engine: Annotated[str | None, ENGINE_OPTION] = None,
    top_k: Annotated[int | None, TOP_K_OPTION] = None,
    score_profile: Annotated[str | None, SCORE_PROFILE_OPTION] = None,
) -> None:
    """Generate strict canon candidates and write export/report artifacts."""
    extra_options = _generate_extra_options()
    payload = _run_generate_command(
        input_path=input_path,
        out=out,
        options=GenerateCommandOptions(
            config_path=config_path,
            chord_policy=extra_options.chord_policy,
            engine=engine,
            top_k=top_k,
            score_profile=score_profile,
            overwrite=extra_options.overwrite,
        ),
    )
    console.print_json(data=payload)


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def polish(
    run_dir: Annotated[Path, _argument(file_okay=False, help="Generated run directory.")],
    candidate_id: Annotated[str, CANDIDATE_ID_OPTION],
    bars: Annotated[str, BARS_OPTION],
    top_k: Annotated[int, TOP_K_OPTION] = 6,
) -> None:
    """Generate selected-bar local rewrite variants for an existing run candidate."""
    extra_options = _polish_extra_options()
    try:
        bar_start, bar_end = _parse_bar_range(bars)
        request = PolishRequest.model_validate(
            {
                "bar_start": bar_start,
                "bar_end": bar_end,
                "lock_voice": normalize_cli_token(extra_options.lock_voice),
                "rewrite_voice": normalize_cli_token(extra_options.rewrite_voice),
                "max_variants": top_k,
                "objective_preset": normalize_cli_token(extra_options.preset),
            }
        )
        result = polish_run_candidate(run_dir, candidate_id, request)
    except KithaironError as exc:
        _exit_project_error(exc)
    except ValidationError as exc:
        _exit_validation_error(exc, code="polish_request_invalid")
    except Exception as exc:
        _exit_unexpected_error(exc)

    console.print_json(data=result.model_dump(mode="json"))


def _run_generate_command(
    *,
    input_path: Path,
    out: Path,
    options: GenerateCommandOptions,
) -> dict[str, object]:
    overrides = build_config_overrides(
        ConfigOverrideOptions(
            chord_policy=options.chord_policy,
            engine=options.engine,
            top_k=options.top_k,
            score_profile=options.score_profile,
        )
    )
    try:
        config = load_config(options.config_path, overrides)
        generation = run_generation(input_path, out, config, overwrite_output=options.overwrite)
    except KithaironError as exc:
        _exit_project_error(exc)
    except Exception as exc:
        _exit_unexpected_error(exc)

    return _generation_success_payload(generation)


def _generate_extra_options() -> ExtraCommandOptions:
    context = get_current_context(silent=True)
    return _parse_extra_options(
        [] if context is None else list(context.args),
        allow_overwrite=True,
    )


def _resolve_extra_options() -> ExtraCommandOptions:
    context = get_current_context(silent=True)
    return _parse_extra_options(
        [] if context is None else list(context.args),
        allow_overwrite=False,
    )


def _polish_extra_options() -> PolishCommandOptions:
    context = get_current_context(silent=True)
    return _parse_polish_extra_options([] if context is None else list(context.args))


_POLISH_EXTRA_FIELDS = {
    "--lock-voice": "lock_voice",
    "--rewrite-voice": "rewrite_voice",
    "--preset": "preset",
}


def _parse_polish_extra_options(extra_args: list[str]) -> PolishCommandOptions:
    values = {
        "lock_voice": "none",
        "rewrite_voice": "auto",
        "preset": "general-polish",
    }
    index = 0
    while index < len(extra_args):
        option, separator, inline_value = extra_args[index].partition("=")
        field = _POLISH_EXTRA_FIELDS.get(option)
        if field is None:
            raise UsageError(f"Unsupported option or argument: {extra_args[index]}")
        values[field] = (
            inline_value if separator else _required_extra_option_value(extra_args, index, option)
        )
        index += 1 if separator else 2
    return PolishCommandOptions(
        lock_voice=values["lock_voice"],
        rewrite_voice=values["rewrite_voice"],
        preset=values["preset"],
    )


def _required_extra_option_value(extra_args: list[str], index: int, option: str) -> str:
    try:
        return extra_args[index + 1]
    except IndexError as exc:
        raise UsageError(f"{option} requires a value") from exc


def _parse_extra_options(extra_args: list[str], *, allow_overwrite: bool) -> ExtraCommandOptions:
    overwrite = overwrite_output
    chord_policy: str | None = None
    score_profile: str | None = None
    index = 0
    while index < len(extra_args):
        arg = extra_args[index]
        if arg == "--overwrite":
            if not allow_overwrite:
                raise UsageError(f"Unsupported option or argument: {arg}")
            overwrite = True
            index += 1
        elif arg == "--score-profile":
            try:
                score_profile = extra_args[index + 1]
            except IndexError as exc:
                raise UsageError("--score-profile requires a value") from exc
            index += 2
        elif arg.startswith("--score-profile="):
            score_profile = arg.split("=", maxsplit=1)[1]
            index += 1
        elif arg == "--chord-policy":
            try:
                chord_policy = extra_args[index + 1]
            except IndexError as exc:
                raise UsageError("--chord-policy requires a value") from exc
            index += 2
        elif arg.startswith("--chord-policy="):
            chord_policy = arg.split("=", maxsplit=1)[1]
            index += 1
        else:
            raise UsageError(f"Unsupported option or argument: {arg}")
    return ExtraCommandOptions(
        chord_policy=chord_policy,
        overwrite=overwrite,
        score_profile=score_profile,
    )


def _parse_bar_range(value: str) -> tuple[int, int]:
    start_text, separator, end_text = value.strip().partition("-")
    if not start_text or (separator and not end_text):
        raise KithaironError(
            "Bar range must be a positive integer or inclusive range like 7-8.",
            code="polish_invalid_bar_range",
            details={"bars": value},
        )
    try:
        start = int(start_text)
        end = int(end_text) if separator else start
    except ValueError as exc:
        raise KithaironError(
            "Bar range must be a positive integer or inclusive range like 7-8.",
            code="polish_invalid_bar_range",
            details={"bars": value},
        ) from exc
    if start < 1 or end < start:
        raise KithaironError(
            "Bar range must start at bar 1 or later and end after the start.",
            code="polish_invalid_bar_range",
            details={"bars": value, "bar_start": start, "bar_end": end},
        )
    return start, end


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


@config_app.command(
    "resolve", context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def resolve_config(
    config_path: Annotated[Path | None, CONFIG_PATH_OPTION] = None,
    out: Annotated[Path | None, OUT_PATH_OPTION] = None,
    output_format: Annotated[Literal["toml", "json"], FORMAT_OPTION] = "toml",
    engine: Annotated[str | None, ENGINE_OPTION] = None,
    top_k: Annotated[int | None, TOP_K_OPTION] = None,
    score_profile: Annotated[str | None, SCORE_PROFILE_OPTION] = None,
) -> None:
    """Load config defaults, apply overrides, and print or write the resolved config."""
    extra_options = _resolve_extra_options()
    overrides = build_config_overrides(
        ConfigOverrideOptions(
            chord_policy=extra_options.chord_policy,
            engine=engine,
            top_k=top_k,
            score_profile=score_profile,
        )
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


def _exit_validation_error(exc: ValidationError, *, code: str) -> NoReturn:
    console.print_json(
        data=Diagnostic(
            code=code,
            message="Command options are invalid.",
            details={"errors": exc.errors(include_url=False)},
        ).to_dict()
    )
    raise typer.Exit(code=1) from exc


def main() -> None:
    """Run the canonize command line application."""
    app()
