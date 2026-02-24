"""TraceGraph model — root container for a single trace."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, computed_field, model_validator

from .edge import Edge
from .node import Node, NodeStatus

CURRENT_SCHEMA_VERSION = "0.1.0"


class TraceGraph(BaseModel):
    """Root trace structure containing nodes and edges."""

    model_config = ConfigDict(strict=True, extra="ignore")

    schema_version: str = CURRENT_SCHEMA_VERSION
    trace_id: str = Field(default_factory=lambda: uuid4().hex)
    name: str = ""
    nodes: dict[str, Node] = Field(default_factory=dict)
    edges: list[Edge] = Field(default_factory=list)
    start_time: datetime | None = None
    end_time: datetime | None = None
    metadata: dict[str, object] = Field(default_factory=dict)

    _sequence_counter: int = PrivateAttr(default=0)

    @computed_field(return_type=float | None)
    @property
    def duration_ms(self) -> float | None:
        if self.start_time is None or self.end_time is None:
            return None
        return (self.end_time - self.start_time).total_seconds() * 1000.0

    @property
    def root_nodes(self) -> list[Node]:
        return [node for node in self.nodes.values() if node.parent_id is None]

    @property
    def failed_nodes(self) -> list[Node]:
        return [node for node in self.nodes.values() if node.status == NodeStatus.FAILED]

    def next_sequence_number(self) -> int:
        value = self._sequence_counter
        self._sequence_counter += 1
        return value

    def add_node(self, node: Node) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        if edge.source_id not in self.nodes:
            raise ValueError(f"Unknown edge source node id: {edge.source_id}")
        if edge.target_id not in self.nodes:
            raise ValueError(f"Unknown edge target node id: {edge.target_id}")
        self.edges.append(edge)

    @model_validator(mode="after")
    def validate_edge_references(self) -> TraceGraph:
        for edge in self.edges:
            if edge.source_id not in self.nodes:
                raise ValueError(f"Edge source_id not found in nodes: {edge.source_id}")
            if edge.target_id not in self.nodes:
                raise ValueError(f"Edge target_id not found in nodes: {edge.target_id}")
        return self
