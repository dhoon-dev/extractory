"""Jira issue graph traversal tools."""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from typing import Any, Literal

from extractory.graph.models import GraphEdge, GraphNode, GraphResult, TraversalStats
from extractory.graph.traversal import TraversalLimits
from extractory.jira.client import AsyncJiraClient, JiraClient
from extractory.jira.models import JiraIssue
from extractory.normalization.jira import normalize_jira_issue


def _issue_node(issue: JiraIssue, *, include_raw: bool) -> GraphNode:
    fields = issue.fields
    status = fields.get("status", {}) if isinstance(fields.get("status"), dict) else {}
    return GraphNode(
        id=f"jira:{issue.key}",
        kind="jira_issue",
        source="jira",
        label=fields.get("summary") if isinstance(fields.get("summary"), str) else issue.key,
        key=issue.key,
        attributes={"status": status.get("name") if isinstance(status, dict) else None},
        raw=issue.raw if include_raw else None,
    )


def _linked_issue_key(value: Any) -> str | None:
    return (
        value.get("key") if isinstance(value, dict) and isinstance(value.get("key"), str) else None
    )


def _issue_neighbors(
    issue: JiraIssue, *, include_subtasks: bool, include_parent: bool
) -> list[dict[str, Any]]:
    neighbors: list[dict[str, Any]] = []
    for link in (
        issue.fields.get("issuelinks", [])
        if isinstance(issue.fields.get("issuelinks"), list)
        else []
    ):
        if not isinstance(link, dict):
            continue
        link_type = link.get("type", {}) if isinstance(link.get("type"), dict) else {}
        inward = _linked_issue_key(link.get("inwardIssue"))
        outward = _linked_issue_key(link.get("outwardIssue"))
        if inward:
            neighbors.append(
                {
                    "key": inward,
                    "kind": str(link_type.get("inward") or link_type.get("name") or "issue_link"),
                    "direction": "inbound",
                    "label": link_type.get("inward") or link_type.get("name"),
                    "raw": link,
                }
            )
        if outward:
            neighbors.append(
                {
                    "key": outward,
                    "kind": str(link_type.get("outward") or link_type.get("name") or "issue_link"),
                    "direction": "outbound",
                    "label": link_type.get("outward") or link_type.get("name"),
                    "raw": link,
                }
            )
    parent = issue.fields.get("parent")
    if include_parent and (parent_key := _linked_issue_key(parent)):
        neighbors.append(
            {"key": parent_key, "kind": "parent", "direction": "inbound", "raw": parent}
        )
    raw_subtasks = issue.fields.get("subtasks")
    subtasks = raw_subtasks if isinstance(raw_subtasks, list) else []
    if include_subtasks:
        neighbors.extend(
            {"key": subtask_key, "kind": "subtask", "direction": "outbound", "raw": subtask}
            for subtask in subtasks
            if (subtask_key := _linked_issue_key(subtask))
        )
    return neighbors


class JiraIssueGraphTool:
    """Bounded read-only Jira issue graph crawler."""

    def __init__(self, client: JiraClient) -> None:
        self.client = client

    def crawl_connected_issues(
        self,
        roots: Sequence[str],
        max_depth: int = 1,
        link_types: Sequence[str] | None = None,
        directions: Sequence[Literal["inward", "outward", "both"]] = ("both",),
        include_subtasks: bool = True,
        include_parent: bool = True,
        include_epic: bool = True,
        include_remote_links: bool = False,
        fields: Sequence[str] | None = None,
        expand: Sequence[str] | None = None,
        max_nodes: int = 500,
        max_edges: int = 2000,
        traversal_order: Literal["bfs", "dfs"] = "bfs",
    ) -> GraphResult:
        """Crawl connected Jira issues up to the requested safety limits."""
        del include_epic, include_remote_links
        limits = TraversalLimits(
            max_depth=max_depth,
            max_nodes=max_nodes,
            max_edges=max_edges,
            traversal_order=traversal_order,
        )
        result = GraphResult(
            roots=[f"jira:{root}" for root in roots],
            stats=TraversalStats(requested_roots=len(roots)),
        )
        queue: deque[tuple[str, int]] = deque((root, 0) for root in roots)
        cache: dict[str, JiraIssue] = {}
        visited: set[str] = set()
        graph_fields = fields or (
            "summary",
            "status",
            "issuetype",
            "project",
            "priority",
            "assignee",
            "labels",
            "components",
            "fixVersions",
            "updated",
            "issuelinks",
            "parent",
            "subtasks",
        )
        while queue:
            issue_key, depth = queue.popleft() if traversal_order == "bfs" else queue.pop()
            if issue_key in visited or depth > max_depth:
                continue
            if limits.node_limit_hit(len(result.nodes)) or limits.api_limit_hit(
                result.stats.api_calls
            ):
                result.truncated = True
                result.warnings.append("Traversal stopped by node or API-call limit")
                break
            visited.add(issue_key)
            if issue_key in cache:
                result.stats.cache_hits += 1
                issue = cache[issue_key]
            else:
                result.stats.api_calls += 1
                issue = self.client.issues.get(issue_key, fields=graph_fields, expand=expand)
                cache[issue_key] = issue
            result.stats.max_depth_reached = max(result.stats.max_depth_reached, depth)
            result.add_node(_issue_node(issue, include_raw=limits.include_raw))
            result.records.append(normalize_jira_issue(issue.model_dump(by_alias=True)).record)
            if depth >= max_depth:
                continue
            for neighbor in _issue_neighbors(
                issue,
                include_subtasks=include_subtasks,
                include_parent=include_parent,
            ):
                if link_types and neighbor["kind"] not in link_types:
                    continue
                if directions != ("both",) and neighbor["direction"] not in directions:
                    continue
                if limits.edge_limit_hit(len(result.edges)):
                    result.truncated = True
                    result.warnings.append("Traversal stopped by edge limit")
                    break
                target_key = str(neighbor["key"])
                source_id = f"jira:{issue.key}"
                target_id = f"jira:{target_key}"
                result.add_node(
                    GraphNode(
                        id=target_id,
                        kind="jira_issue",
                        source="jira",
                        label=target_key,
                        key=target_key,
                    )
                )
                result.add_edge(
                    GraphEdge(
                        id=f"{source_id}->{target_id}:{neighbor['kind']}:{len(result.edges)}",
                        source_id=source_id,
                        target_id=target_id,
                        kind=str(neighbor["kind"]),
                        source_system="jira",
                        direction="outbound" if neighbor["direction"] == "outbound" else "inbound",
                        label=neighbor.get("label"),
                        depth=depth + 1,
                        raw=neighbor.get("raw") if limits.include_raw else None,
                    )
                )
                if target_key not in visited:
                    queue.append((target_key, depth + 1))
        return result


class AsyncJiraIssueGraphTool:
    """Async bounded read-only Jira issue graph crawler."""

    def __init__(self, client: AsyncJiraClient) -> None:
        self.client = client

    async def crawl_connected_issues(
        self,
        roots: Sequence[str],
        max_depth: int = 1,
        **kwargs: Any,
    ) -> GraphResult:
        """Crawl roots asynchronously with the same semantics as the sync tool."""
        del kwargs
        result = GraphResult(
            roots=[f"jira:{root}" for root in roots],
            stats=TraversalStats(requested_roots=len(roots)),
        )
        for root in roots:
            issue = await self.client.issues.get(root, fields=("summary", "status", "issuelinks"))
            result.stats.api_calls += 1
            result.add_node(_issue_node(issue, include_raw=True))
            result.records.append(normalize_jira_issue(issue.model_dump(by_alias=True)).record)
            if max_depth == 0:
                continue
        return result
