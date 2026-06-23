"""Gerrit related change graph tools."""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from typing import Any, Literal

from extractory.gerrit.client import AsyncGerritClient, GerritClient
from extractory.gerrit.models import GerritChangeInfo
from extractory.graph.models import GraphEdge, GraphNode, GraphResult, TraversalStats
from extractory.normalization.gerrit import normalize_gerrit_change


def _change_node(change: GerritChangeInfo) -> GraphNode:
    return GraphNode(
        id=f"gerrit:{change.change_number}",
        kind="gerrit_change",
        source="gerrit",
        label=change.subject,
        key=str(change.change_number),
        attributes={"project": change.project, "branch": change.branch, "status": change.status},
        raw=change.raw,
    )


class GerritChangeGraphTool:
    """Bounded read-only Gerrit related-change crawler."""

    def __init__(self, client: GerritClient) -> None:
        self.client = client

    def crawl_related_changes(
        self,
        roots: Sequence[str],
        max_depth: int = 1,
        include_related: bool = True,
        include_submitted_together: bool = True,
        include_same_topic: bool = True,
        include_cherry_picks: bool = True,
        include_reverts: bool = True,
        include_files: bool = False,
        include_comments: bool = False,
        options_preset: Literal["minimal", "standard", "detailed", "full"] = "standard",
        max_nodes: int = 500,
        max_edges: int = 2000,
    ) -> GraphResult:
        """Crawl Gerrit related changes up to safety limits."""
        del include_cherry_picks, include_reverts, include_files, include_comments
        result = GraphResult(
            roots=[f"gerrit:{root}" for root in roots],
            stats=TraversalStats(requested_roots=len(roots)),
        )
        queue: deque[tuple[str, int]] = deque((root, 0) for root in roots)
        visited: set[str] = set()
        while queue:
            change_id, depth = queue.popleft()
            if change_id in visited or depth > max_depth:
                continue
            if len(result.nodes) >= max_nodes:
                result.truncated = True
                result.warnings.append("Traversal stopped by node limit")
                break
            visited.add(change_id)
            result.stats.api_calls += 1
            change = self.client.changes.get(change_id, option_preset=options_preset)
            result.add_node(_change_node(change))
            result.records.append(normalize_gerrit_change(change.model_dump(by_alias=True)).record)
            if depth >= max_depth:
                continue
            if include_related:
                related = self.client.changes.get_related(str(change.change_number))
                for item in (
                    related.get("changes", []) if isinstance(related.get("changes"), list) else []
                ):
                    _add_related_edge(
                        result, change, item, "related_change", depth, max_edges, queue
                    )
            if include_submitted_together:
                submitted = self.client.changes.get_submitted_together(str(change.change_number))
                changes = (
                    submitted.get("changes", [])
                    if isinstance(submitted.get("changes"), list)
                    else []
                )
                for item in changes:
                    _add_related_edge(
                        result, change, item, "submitted_together", depth, max_edges, queue
                    )
            if include_same_topic and change.topic:
                for item in self.client.changes.query(
                    f"topic:{change.topic}", option_preset="minimal"
                ):
                    _add_related_edge(
                        result,
                        change,
                        item.model_dump(by_alias=True),
                        "same_topic",
                        depth,
                        max_edges,
                        queue,
                    )
        return result


def _add_related_edge(
    result: GraphResult,
    source: GerritChangeInfo,
    item: Any,
    kind: str,
    depth: int,
    max_edges: int,
    queue: deque[tuple[str, int]],
) -> None:
    if not isinstance(item, dict):
        return
    number = item.get("_number") or item.get("change_number")
    if number is None or int(number) == source.change_number:
        return
    if len(result.edges) >= max_edges:
        result.truncated = True
        result.warnings.append("Traversal stopped by edge limit")
        return
    target_id = f"gerrit:{number}"
    result.add_node(
        GraphNode(
            id=target_id,
            kind="gerrit_change",
            source="gerrit",
            label=item.get("subject"),
            key=str(number),
            attributes={"project": item.get("project"), "branch": item.get("branch")},
            raw=item,
        )
    )
    result.add_edge(
        GraphEdge(
            id=f"gerrit:{source.change_number}->{target_id}:{kind}:{len(result.edges)}",
            source_id=f"gerrit:{source.change_number}",
            target_id=target_id,
            kind=kind,
            source_system="gerrit",
            direction="unknown",
            depth=depth + 1,
            raw=item,
        )
    )
    queue.append((str(number), depth + 1))


class AsyncGerritChangeGraphTool:
    """Async bounded read-only Gerrit related-change crawler."""

    def __init__(self, client: AsyncGerritClient) -> None:
        self.client = client

    async def crawl_related_changes(
        self, roots: Sequence[str], max_depth: int = 1, **kwargs: Any
    ) -> GraphResult:
        """Fetch root changes asynchronously."""
        del max_depth, kwargs
        result = GraphResult(
            roots=[f"gerrit:{root}" for root in roots],
            stats=TraversalStats(requested_roots=len(roots)),
        )
        for root in roots:
            change = await self.client.changes.get(root, option_preset="standard")
            result.stats.api_calls += 1
            result.add_node(_change_node(change))
            result.records.append(normalize_gerrit_change(change.model_dump(by_alias=True)).record)
        return result
