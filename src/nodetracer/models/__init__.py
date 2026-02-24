"""Data models for trace capture."""

from .edge import Edge, EdgeType
from .node import Node, NodeStatus, NodeType
from .trace_graph import CURRENT_SCHEMA_VERSION, TraceGraph

__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "Edge",
    "EdgeType",
    "Node",
    "NodeStatus",
    "NodeType",
    "TraceGraph",
]
