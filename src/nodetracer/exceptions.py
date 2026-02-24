"""Public exception types for nodetracer."""

from __future__ import annotations


class NodetracerError(Exception):
    """Base class for all nodetracer exceptions."""


class NodetracerLoadError(NodetracerError):
    """Raised when a trace file cannot be loaded or parsed."""
