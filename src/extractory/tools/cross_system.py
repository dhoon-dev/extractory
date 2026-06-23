"""Cross-system Jira and Gerrit analysis helpers."""

from __future__ import annotations

from collections.abc import Sequence

from extractory.correlation import correlate_issue_keys
from extractory.gerrit.client import GerritClient
from extractory.graph.models import GraphEdge, GraphNode, GraphResult
from extractory.jira.client import JiraClient
from extractory.records import IssueChangeLinkRecord
from extractory.tools.gerrit_graph import GerritChangeGraphTool
from extractory.tools.jira_graph import JiraIssueGraphTool
from extractory.tools.summaries import ReleaseReadinessReport, RiskSummary


def find_gerrit_changes_for_issue(
    client: GerritClient,
    issue_key: str,
    *,
    query_base: str | None = None,
) -> list[IssueChangeLinkRecord]:
    """Find Gerrit changes that mention a Jira issue key."""
    query = f"{query_base or ''} {issue_key}".strip()
    links: list[IssueChangeLinkRecord] = []
    for change in client.changes.query_all(query, option_preset="standard"):
        links.extend(correlate_issue_keys(change.model_dump(by_alias=True)))
    return [link for link in links if link.issue_key == issue_key]


def find_gerrit_changes_for_issues(
    client: GerritClient,
    issue_keys: Sequence[str],
    *,
    query_base: str | None = None,
) -> list[IssueChangeLinkRecord]:
    """Find Gerrit changes for multiple issue keys."""
    records: list[IssueChangeLinkRecord] = []
    for issue_key in issue_keys:
        records.extend(find_gerrit_changes_for_issue(client, issue_key, query_base=query_base))
    return records


def build_issue_change_graph(
    jira_client: JiraClient,
    gerrit_client: GerritClient,
    issue_keys: Sequence[str],
    *,
    jira_depth: int = 1,
    gerrit_depth: int = 1,
    include_jira_links: bool = True,
    include_gerrit_related: bool = True,
    include_files: bool = False,
    include_comments: bool = False,
) -> GraphResult:
    """Build a graph connecting Jira issues and Gerrit changes by issue keys."""
    graph = GraphResult(roots=[f"jira:{key}" for key in issue_keys])
    if include_jira_links:
        jira_graph = JiraIssueGraphTool(jira_client).crawl_connected_issues(
            issue_keys, max_depth=jira_depth
        )
        graph.nodes.extend(jira_graph.nodes)
        graph.edges.extend(jira_graph.edges)
        graph.records.extend(jira_graph.records)
        graph.warnings.extend(jira_graph.warnings)
    links = find_gerrit_changes_for_issues(gerrit_client, issue_keys)
    change_numbers = [str(link.change_number) for link in links if link.change_number is not None]
    if include_gerrit_related and change_numbers:
        gerrit_graph = GerritChangeGraphTool(gerrit_client).crawl_related_changes(
            change_numbers,
            max_depth=gerrit_depth,
            include_files=include_files,
            include_comments=include_comments,
        )
        graph.nodes.extend(gerrit_graph.nodes)
        graph.edges.extend(gerrit_graph.edges)
        graph.records.extend(gerrit_graph.records)
        graph.warnings.extend(gerrit_graph.warnings)
    for link in links:
        if link.change_number is None:
            continue
        issue_id = f"jira:{link.issue_key}"
        change_id = f"gerrit:{link.change_number}"
        graph.add_node(GraphNode(id=issue_id, kind="jira_issue", source="jira", key=link.issue_key))
        graph.add_node(
            GraphNode(
                id=change_id, kind="gerrit_change", source="gerrit", key=str(link.change_number)
            )
        )
        graph.add_edge(
            GraphEdge(
                id=f"{issue_id}->{change_id}:issue_mentions_change:{len(graph.edges)}",
                source_id=issue_id,
                target_id=change_id,
                kind="issue_mentions_change",
                source_system="derived",
                direction="undirected",
                label=link.match_source,
                raw=link.model_dump(),
            )
        )
        graph.records.append(link)
    graph.stats.visited_nodes = len(graph.nodes)
    graph.stats.visited_edges = len(graph.edges)
    return graph


def summarize_release_readiness(
    jira_client: JiraClient,
    gerrit_client: GerritClient,
    project_key: str,
    version_name: str,
    *,
    gerrit_query_base: str | None = None,
) -> ReleaseReadinessReport:
    """Summarize release readiness across Jira and Gerrit."""
    from extractory.tools.jira_release import collect_issues_by_fix_version

    issues = collect_issues_by_fix_version(jira_client, project_key, version_name)
    links = find_gerrit_changes_for_issues(
        gerrit_client,
        [issue.issue_key for issue in issues],
        query_base=gerrit_query_base,
    )
    graph = build_issue_change_graph(
        jira_client,
        gerrit_client,
        [issue.issue_key for issue in issues],
        jira_depth=1,
        gerrit_depth=1,
    )
    return ReleaseReadinessReport(
        project_key=project_key,
        version_name=version_name,
        jira_issue_count=len(issues),
        jira_unresolved_count=sum(issue.status_category != "Done" for issue in issues),
        gerrit_change_count=len({link.change_number for link in links if link.change_number}),
        issues_without_gerrit_changes=[
            issue.issue_key
            for issue in issues
            if issue.issue_key not in {link.issue_key for link in links}
        ],
        graph=graph,
    )


def summarize_change_risk(
    *,
    issue_keys: Sequence[str] | None = None,
    gerrit_query: str | None = None,
) -> RiskSummary:
    """Return a deterministic heuristic risk summary."""
    score = 0
    reasons: list[str] = []
    if issue_keys:
        score += len(issue_keys) * 5
        reasons.append("Jira issues are in scope")
    if gerrit_query:
        score += 10
        reasons.append("Gerrit query is in scope")
    level = "low" if score < 20 else "medium" if score < 50 else "high"
    return RiskSummary(risk_score=score, risk_level=level, reasons=reasons)
