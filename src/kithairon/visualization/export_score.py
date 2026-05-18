"""External score rendering helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Literal

type RenderFormat = Literal["pdf", "svg", "png"]


class ExternalScoreRenderError(RuntimeError):
    """Raised when an external score renderer fails."""


def render_with_musescore(
    musicxml_path: Path,
    output_path: Path,
    fmt: RenderFormat,
    musescore_bin: Path,
    *,
    timeout_seconds: int = 30,
) -> Path:
    """Render a MusicXML score to PDF/SVG/PNG with MuseScore CLI."""
    if output_path.suffix.lower().lstrip(".") != fmt:
        raise ExternalScoreRenderError(f"Output path suffix does not match render format: {fmt}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        completed = subprocess.run(
            [str(musescore_bin), "-o", str(output_path), str(musicxml_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except OSError as exc:
        raise ExternalScoreRenderError(f"Could not run MuseScore CLI: {musescore_bin}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ExternalScoreRenderError("MuseScore rendering timed out.") from exc

    if completed.returncode != 0:
        raise ExternalScoreRenderError(
            "MuseScore rendering failed: "
            + (completed.stderr.strip() or completed.stdout.strip() or "unknown error")
        )
    if not output_path.exists():
        raise ExternalScoreRenderError("MuseScore did not create the expected output file.")
    return output_path
