"""Configuration for a Tracer instance."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

CaptureLevel = Literal["minimal", "standard", "full"]


class TracerConfig(BaseModel):
    """Validated configuration for a Tracer. Passed via DI at construction."""

    capture_level: CaptureLevel = "full"
    auto_instrument: list[str] = []
    redact_patterns: list[str] = []
    max_output_size: int | None = None
    max_input_size: int | None = None
