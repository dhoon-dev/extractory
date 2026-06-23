"""Generic graph models for Jira, Gerrit, and derived relationships."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

NodeKind = Literal[
    "jira_issue",
    "gerrit_change",
    "gerrit_revision",
    "gerrit_commit",
    "gerrit_file",
    "user",
    "version",
    "component",
]
GraphSource = Literal["jira", "gerrit", "derived"]
EdgeDirection = Literal["outbound", "inbound", "undirected", "unknown"]


class GraphNode(BaseModel):
    """Node in a lightweight node-link graph."""

    model_config = ConfigDict(extra="allow")

    id: str
    kind: NodeKind
    source: GraphSource
    label: str | None = None
    key: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] | None = None


class GraphEdge(BaseModel):
    """Edge in a lightweight node-link graph."""

    model_config = ConfigDict(extra="allow")

    id: str
    source_id: str
    target_id: str
    kind: str
    source_system: GraphSource
    direction: EdgeDirection = "unknown"
    label: str | None = None
    depth: int | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] | None = None


class TraversalStats(BaseModel):
    """Bounded traversal statistics."""

    requested_roots: int = 0
    visited_nodes: int = 0
    visited_edges: int = 0
    max_depth_reached: int = 0
    api_calls: int = 0
    cache_hits: int = 0
    skipped_nodes: int = 0
    skipped_edges: int = 0
    elapsed_seconds: float | None = None


class GraphResult(BaseModel):
    """Graph traversal output."""

    roots: list[str] = Field(default_factory=list)
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    records: list[Any] = Field(default_factory=list)
    stats: TraversalStats = Field(default_factory=TraversalStats)
    warnings: list[str] = Field(default_factory=list)
    truncated: bool = False

    def add_node(self, node: GraphNode) -> bool:
        """Add a node if it is not already present."""
        if any(existing.id == node.id for existing in self.nodes):
            return False
        self.nodes.append(node)
        self.stats.visited_nodes = len(self.nodes)
        return True

    def add_edge(self, edge: GraphEdge) -> bool:
        """Add an edge, preserving duplicate relationships with unique ids."""
        if any(existing.id == edge.id for existing in self.edges):
            return False
        self.edges.append(edge)
        self.stats.visited_edges = len(self.edges)
        return True
