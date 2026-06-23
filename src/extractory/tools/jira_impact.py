"""Jira impact and dependency helpers."""

from __future__ import annotations

from collections.abc import Sequence

from extractory.jira.client import JiraClient
from extractory.tools.jira_graph import JiraIssueGraphTool
from extractory.tools.summaries import DependencyClosureResult


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
    graph = JiraIssueGraphTool(client).crawl_connected_issues([issue_key], max_depth=1)
    blockers: list[str] = []
    unresolved: list[str] = []
    resolved: list[str] = []
    node_by_id = {node.id: node for node in graph.nodes}
    for edge in graph.edges:
        if edge.kind not in blocking and edge.label not in blocking:
            continue
        key = edge.target_id.removeprefix("jira:")
        blockers.append(key)
        status = node_by_id.get(edge.target_id, node_by_id.get(edge.source_id))
        status_category = status.attributes.get("status") if status else None
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
