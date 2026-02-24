"""Public exception types for logtracer."""

from __future__ import annotations


class LogtracerError(Exception):
    """Base class for all logtracer exceptions."""


class LogtracerLoadError(LogtracerError):
    """Raised when a trace file cannot be loaded or parsed."""
