"""Jira impact and dependency helpers."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from extractory.graph.models import GraphEdge, GraphNode, GraphResult
from extractory.jira.client import JiraClient
from extractory.jira.models import JiraIssue
from extractory.tools.summaries import DependencyClosureResult


def _linked_issue_key(value: Any) -> str | None:
    return (
        value.get("key") if isinstance(value, dict) and isinstance(value.get("key"), str) else None
    )


def _linked_issues(issue: JiraIssue) -> list[dict[str, Any]]:
    links = issue.fields.get("issuelinks", [])
    if not isinstance(links, list):
        return []
    linked: list[dict[str, Any]] = []
    for link in links:
        if not isinstance(link, dict):
            continue
        link_type = link.get("type", {}) if isinstance(link.get("type"), dict) else {}
        for issue_key, direction in (("inwardIssue", "inbound"), ("outwardIssue", "outbound")):
            if key := _linked_issue_key(link.get(issue_key)):
                label = link_type.get("inward" if issue_key == "inwardIssue" else "outward")
                linked.append(
                    {
                        "key": key,
                        "kind": str(label or link_type.get("name") or "issue_link"),
                        "direction": direction,
                        "label": label or link_type.get("name"),
                        "raw": link,
                    }
                )
    return linked


def _issue_node(issue: JiraIssue) -> GraphNode:
    status = issue.fields.get("status", {})
    return GraphNode(
        id=f"jira:{issue.key}",
        kind="jira_issue",
        source="jira",
        key=issue.key,
        label=issue.fields.get("summary")
        if isinstance(issue.fields.get("summary"), str)
        else issue.key,
        attributes={"status": status.get("name") if isinstance(status, dict) else None},
        raw=issue.raw,
    )


def check_dependency_closure(
    client: JiraClient,
    issue_key: str,
    *,
    blocking_link_types: Sequence[str] | None = None,
    done_status_categories: Sequence[str] | None = None,
) -> DependencyClosureResult:
    """Check whether a Jira issue appears blocked by linked issues."""
    blocking = set(blocking_link_types or ("Blocks", "blocks", "Dependency", "depends on"))
    done = set(done_status_categories or ("Done",))
    graph = GraphResult(roots=[f"jira:{issue_key}"])
    root = client.issues.get(issue_key, fields=("summary", "status", "issuelinks"))
    graph.stats.api_calls += 1
    graph.add_node(_issue_node(root))
    blockers: list[str] = []
    unresolved: list[str] = []
    resolved: list[str] = []
    for linked in _linked_issues(root):
        if linked["kind"] not in blocking and linked["label"] not in blocking:
            continue
        key = str(linked["key"])
        blockers.append(key)
        linked_issue = client.issues.get(key, fields=("summary", "status"))
        graph.stats.api_calls += 1
        graph.add_node(_issue_node(linked_issue))
        graph.add_edge(
            GraphEdge(
                id=f"jira:{issue_key}->jira:{key}:{linked['kind']}:{len(graph.edges)}",
                source_id=f"jira:{issue_key}",
                target_id=f"jira:{key}",
                kind=str(linked["kind"]),
                source_system="jira",
                direction="outbound" if linked["direction"] == "outbound" else "inbound",
                label=linked["label"],
                raw=linked["raw"],
            )
        )
        status_category = linked_issue.fields.get("status", {})
        status_category = status_category.get("name") if isinstance(status_category, dict) else None
        if status_category in done:
            resolved.append(key)
        else:
            unresolved.append(key)
    return DependencyClosureResult(
        issue_key=issue_key,
        is_blocked=bool(unresolved),
        blocking_issues=blockers,
        unresolved_blockers=unresolved,
        resolved_blockers=resolved,
        graph=graph,
        warnings=graph.warnings,
    )
