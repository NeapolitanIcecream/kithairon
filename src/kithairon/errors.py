"""Project exceptions and machine-readable diagnostics."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


def _empty_details() -> Mapping[str, object]:
    return {}


@dataclass(frozen=True)
class Diagnostic:
    """A stable diagnostic payload for CLI output, reports, and tests."""

    code: str
    message: str
    details: Mapping[str, object] = field(default_factory=_empty_details)

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": self.message,
            "details": dict(self.details),
        }


class KithaironError(Exception):
    """Base class for user-facing project errors."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        details: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.diagnostic = Diagnostic(
            code=code,
            message=message,
            details={} if details is None else details,
        )

    def to_diagnostic(self) -> dict[str, object]:
        return self.diagnostic.to_dict()


class ConfigError(KithaironError):
    """Raised when configuration cannot be loaded or validated."""


class ParseError(KithaironError):
    """Raised when an input score cannot be converted to Kithairon IR."""


class TransformError(KithaironError):
    """Raised when a melody transform cannot be applied."""


class GenerationError(KithaironError):
    """Raised when candidate generation or output writing cannot continue."""
