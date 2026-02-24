"""Node model and related enumerations."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field


class NodeStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NodeType(StrEnum):
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    DECISION = "decision"
    RETRIEVAL = "retrieval"
    TRANSFORMATION = "transformation"
    VALIDATION = "validation"
    HUMAN_INPUT = "human_input"
    SUB_AGENT = "sub_agent"
    CUSTOM = "custom"


class Node(BaseModel):
    """Single unit of execution in a trace."""

    model_config = ConfigDict(strict=True, extra="ignore")

    id: str = Field(default_factory=lambda: uuid4().hex)
    sequence_number: int
    name: str
    node_type: str
    status: NodeStatus = NodeStatus.PENDING
    parent_id: str | None = None
    depth: int = 0
    start_time: datetime | None = None
    end_time: datetime | None = None
    input_data: dict[str, object] = Field(default_factory=dict)
    output_data: dict[str, object] = Field(default_factory=dict)
    annotations: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)
    error: str | None = None
    error_type: str | None = None
    error_traceback: str | None = None

    @computed_field(return_type=float | None)
    @property
    def duration_ms(self) -> float | None:
        if self.start_time is None or self.end_time is None:
            return None
        return (self.end_time - self.start_time).total_seconds() * 1000.0
