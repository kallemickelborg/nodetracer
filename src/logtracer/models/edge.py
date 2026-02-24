"""Edge model and edge type enumeration."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class EdgeType(StrEnum):
    CAUSED_BY = "caused_by"
    DATA_FLOW = "data_flow"
    BRANCHED_FROM = "branched_from"
    RETRY_OF = "retry_of"
    FALLBACK_OF = "fallback_of"


class Edge(BaseModel):
    """Directional relationship between two nodes."""

    model_config = ConfigDict(strict=True, extra="ignore")

    source_id: str
    target_id: str
    edge_type: EdgeType = EdgeType.CAUSED_BY
    label: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)
