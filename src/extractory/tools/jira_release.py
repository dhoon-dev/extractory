"""Jira release and hierarchy helpers."""

from __future__ import annotations

from collections import Counter, deque
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from extractory.jira.client import JiraClient
from extractory.jira.models import JiraIssue
from extractory.jira.records import JiraIssueRecord
from extractory.normalization.jira import normalize_jira_issue
from extractory.records import SummaryRecord
from extractory.tools.summaries import (
    HierarchySummary,
    ReleaseSummary,
    StaleIssueRecord,
    summarize_records,
)


def collect_issues_by_fix_version(
    client: JiraClient,
    project_key: str,
    version_name: str,
) -> list[JiraIssueRecord]:
    """Collect normalized Jira issues by project and fixVersion."""
    jql = f'project = "{project_key}" AND fixVersion = "{version_name}"'
    return [
        normalize_jira_issue(issue.model_dump(by_alias=True), include_raw=True).record
        for issue in client.issues.search_all(
            jql, fields=("summary", "status", "fixVersions", "priority")
        )
    ]


def summarize_fix_version(
    client: JiraClient, project_key: str, version_name: str
) -> ReleaseSummary:
    """Summarize a Jira fixVersion using read-only search."""
    issues = collect_issues_by_fix_version(client, project_key, version_name)
    status_counts = Counter(issue.status or "unknown" for issue in issues)
    priority_counts = Counter(issue.priority or "unknown" for issue in issues)
    assignee_counts = Counter(issue.assignee_display_name or "unassigned" for issue in issues)
    component_counts: Counter[str] = Counter()
    for issue in issues:
        component_counts.update(issue.components)
    done_count = status_counts.get("Done", 0)
    return ReleaseSummary(
        project_key=project_key,
        version_name=version_name,
        issue_count=len(issues),
        done_count=done_count,
        unresolved_count=len(issues) - done_count,
        status_counts=dict(status_counts),
        priority_counts=dict(priority_counts),
        assignee_counts=dict(assignee_counts),
        component_counts=dict(component_counts),
        issues=issues,
    )


def find_unresolved_issues_for_version(
    client: JiraClient,
    project_key: str,
    version_name: str,
) -> list[JiraIssueRecord]:
    """Return unresolved issues in a fixVersion."""
    return [
        issue
        for issue in collect_issues_by_fix_version(client, project_key, version_name)
        if issue.status_category != "Done"
    ]


def find_blockers_for_version(
    client: JiraClient,
    project_key: str,
    version_name: str,
    *,
    max_depth: int = 1,
) -> ReleaseSummary:
    """Return a release summary placeholder including graph-friendly blockers."""
    del max_depth
    return summarize_fix_version(client, project_key, version_name)


def build_issue_hierarchy(
    client: JiraClient,
    root_issue_key: str,
    *,
    max_depth: int = 3,
) -> HierarchySummary:
    """Build a compact parent/subtask hierarchy summary."""
    issues: list[JiraIssueRecord] = []
    queue: deque[tuple[str, int]] = deque([(root_issue_key, 0)])
    visited: set[str] = set()
    while queue:
        issue_key, depth = queue.popleft()
        if issue_key in visited or depth > max_depth:
            continue
        visited.add(issue_key)
        issue = client.issues.get(
            issue_key,
            fields=("summary", "status", "issuetype", "assignee", "parent", "subtasks"),
        )
        issues.append(normalize_jira_issue(issue.model_dump(by_alias=True)).record)
        if depth >= max_depth:
            continue
        for subtask_key in _subtask_keys(issue):
            queue.append((subtask_key, depth + 1))
    return _hierarchy_summary(issues)


def build_epic_tree(client: JiraClient, epic_key: str) -> HierarchySummary:
    """Build a compact epic hierarchy summary."""
    return build_issue_hierarchy(client, epic_key, max_depth=3)


def build_subtask_tree(client: JiraClient, issue_key: str) -> HierarchySummary:
    """Build a compact subtask hierarchy summary."""
    return build_issue_hierarchy(client, issue_key, max_depth=1)


def _hierarchy_summary(issues: Iterable[JiraIssueRecord]) -> HierarchySummary:
    issue_list = list(issues)
    status_counts = Counter(issue.status or "unknown" for issue in issue_list)
    issue_type_counts = Counter(issue.issuetype or "unknown" for issue in issue_list)
    assignee_counts = Counter(issue.assignee_display_name or "unassigned" for issue in issue_list)
    return HierarchySummary(
        total_issues=len(issue_list),
        done_count=status_counts.get("Done", 0),
        in_progress_count=status_counts.get("In Progress", 0),
        todo_count=status_counts.get("To Do", 0),
        unresolved_count=len(issue_list) - status_counts.get("Done", 0),
        assignee_counts=dict(assignee_counts),
        status_counts=dict(status_counts),
        issue_type_counts=dict(issue_type_counts),
    )


def _linked_issue_key(value: Any) -> str | None:
    return (
        value.get("key") if isinstance(value, dict) and isinstance(value.get("key"), str) else None
    )


def _subtask_keys(issue: JiraIssue) -> list[str]:
    subtasks = issue.fields.get("subtasks", [])
    if not isinstance(subtasks, list):
        return []
    return [key for subtask in subtasks if (key := _linked_issue_key(subtask))]


def find_stale_issues(
    client: JiraClient,
    jql: str,
    stale_days: int,
    *,
    status_exclude: list[str] | None = None,
) -> list[StaleIssueRecord]:
    """Find issues not updated within the requested number of days."""
    excluded = set(status_exclude or [])
    now = datetime.now(UTC)
    records: list[StaleIssueRecord] = []
    for issue in client.issues.search_all(jql, fields=("summary", "status", "updated", "assignee")):
        normalized = normalize_jira_issue(issue.model_dump(by_alias=True)).record
        if normalized.status in excluded or normalized.updated is None:
            continue
        days = (now - normalized.updated).days
        if days >= stale_days:
            records.append(
                StaleIssueRecord(
                    issue_key=normalized.issue_key,
                    summary=normalized.summary,
                    status=normalized.status,
                    assignee=normalized.assignee_display_name,
                    updated_at=normalized.updated,
                    stale_days=days,
                    priority=normalized.priority,
                    labels=normalized.labels,
                    components=normalized.components,
                    raw=normalized.raw,
                )
            )
    return records


def summarize_stale_issues(records: list[StaleIssueRecord]) -> dict[str, int]:
    """Return a tiny stale issue count summary."""
    return {
        "count": len(records),
        "max_stale_days": max((record.stale_days for record in records), default=0),
    }


def summarize_by_assignee(client: JiraClient, jql: str) -> list[SummaryRecord]:
    """Summarize Jira issues by assignee."""
    records = _search_records(client, jql)
    return summarize_records(records, group_by="assignee", key_getter="assignee_display_name")


def summarize_by_component(client: JiraClient, jql: str) -> list[SummaryRecord]:
    """Summarize Jira issues by first component."""
    records = _search_records(client, jql)
    groups: dict[str, list[str]] = {}
    for record in records:
        key = record.components[0] if record.components else "none"
        groups.setdefault(key, []).append(record.issue_key)
    return [
        SummaryRecord(
            group_by="component", key=key, label=key, count=len(values), issue_keys=values
        )
        for key, values in sorted(groups.items())
    ]


def summarize_by_status(client: JiraClient, jql: str) -> list[SummaryRecord]:
    """Summarize Jira issues by status."""
    return summarize_records(_search_records(client, jql), group_by="status", key_getter="status")


def summarize_by_priority(client: JiraClient, jql: str) -> list[SummaryRecord]:
    """Summarize Jira issues by priority."""
    return summarize_records(
        _search_records(client, jql), group_by="priority", key_getter="priority"
    )


def _search_records(client: JiraClient, jql: str) -> list[JiraIssueRecord]:
    return [
        normalize_jira_issue(issue.model_dump(by_alias=True)).record
        for issue in client.issues.search_all(jql)
    ]
