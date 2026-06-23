"""Traversal limit helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TraversalOrder = Literal["bfs", "dfs"]


@dataclass(slots=True)
class TraversalLimits:
    """Safety limits used by graph tools."""

    max_depth: int = 1
    max_nodes: int = 500
    max_edges: int = 2000
    max_api_calls: int = 1000
    page_size: int = 100
    concurrency: int = 4
    timeout: float | None = None
    include_raw: bool = True
    fail_fast: bool = False
    permission_error_policy: str = "record_warning"
    traversal_order: TraversalOrder = "bfs"

    def node_limit_hit(self, count: int) -> bool:
        """Return whether adding another node would exceed the limit."""
        return count >= self.max_nodes

    def edge_limit_hit(self, count: int) -> bool:
        """Return whether adding another edge would exceed the limit."""
        return count >= self.max_edges

    def api_limit_hit(self, count: int) -> bool:
        """Return whether adding another API call would exceed the limit."""
        return count >= self.max_api_calls
