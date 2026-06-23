"""Shared summary result models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from extractory.graph.models import GraphResult
from extractory.records import SummaryRecord


class DependencyClosureResult(BaseModel):
    """Result for a read-only dependency closure check."""

    issue_key: str
    is_blocked: bool
    blocking_issues: list[str] = Field(default_factory=list)
    unresolved_blockers: list[str] = Field(default_factory=list)
    resolved_blockers: list[str] = Field(default_factory=list)
    graph: GraphResult | None = None
    warnings: list[str] = Field(default_factory=list)


class HierarchySummary(BaseModel):
    """Aggregated Jira hierarchy summary."""

    total_issues: int = 0
    done_count: int = 0
    in_progress_count: int = 0
    todo_count: int = 0
    unresolved_count: int = 0
    assignee_counts: dict[str, int] = Field(default_factory=dict)
    status_counts: dict[str, int] = Field(default_factory=dict)
    issue_type_counts: dict[str, int] = Field(default_factory=dict)


class ReleaseSummary(BaseModel):
    """Read-only Jira release/version summary."""

    project_key: str
    version_name: str
    issue_count: int = 0
    done_count: int = 0
    unresolved_count: int = 0
    blocker_count: int = 0
    unresolved_blocker_count: int = 0
    status_counts: dict[str, int] = Field(default_factory=dict)
    priority_counts: dict[str, int] = Field(default_factory=dict)
    assignee_counts: dict[str, int] = Field(default_factory=dict)
    component_counts: dict[str, int] = Field(default_factory=dict)
    issues: list[Any] = Field(default_factory=list)
    blockers: list[Any] = Field(default_factory=list)
    graph: GraphResult | None = None


class StaleIssueRecord(BaseModel):
    """Stale Jira issue record."""

    issue_key: str
    summary: str | None = None
    status: str | None = None
    assignee: str | None = None
    updated_at: Any | None = None
    stale_days: int
    priority: str | None = None
    labels: list[str] = Field(default_factory=list)
    components: list[str] = Field(default_factory=list)
    raw: dict[str, Any] | None = None


class GerritReviewHealthRecord(BaseModel):
    """Gerrit review-health summary record."""

    change_number: int | None = None
    change_id: str | None = None
    project: str | None = None
    branch: str | None = None
    topic: str | None = None
    subject: str | None = None
    status: str | None = None
    owner: str | None = None
    created_at: Any | None = None
    updated_at: Any | None = None
    age_days: int | None = None
    unresolved_comment_count: int | None = None
    total_comment_count: int | None = None
    insertions: int | None = None
    deletions: int | None = None
    label_summary: dict[str, Any] = Field(default_factory=dict)
    submit_requirement_summary: dict[str, Any] = Field(default_factory=dict)
    reviewer_count: int = 0
    missing_reviewers: bool = False
    has_negative_vote: bool = False
    is_submittable: bool | None = None
    is_work_in_progress: bool = False
    raw: dict[str, Any] | None = None


class GerritFileImpactRecord(BaseModel):
    """Gerrit file impact summary."""

    file_path: str
    project: str | None = None
    branch: str | None = None
    change_count: int = 0
    changes: list[int] = Field(default_factory=list)
    total_insertions: int = 0
    total_deletions: int = 0
    owners: list[str] = Field(default_factory=list)
    reviewers: list[str] = Field(default_factory=list)
    issue_keys: list[str] = Field(default_factory=list)


class SubmissionReadinessResult(BaseModel):
    """Gerrit submitted-together readiness result."""

    root_change: Any | None = None
    submitted_together_changes: list[Any] = Field(default_factory=list)
    non_visible_changes: int = 0
    submittable_count: int = 0
    not_submittable_count: int = 0
    unresolved_comment_count: int = 0
    negative_vote_count: int = 0
    submit_requirement_failures: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    graph: GraphResult | None = None


class IncludedInRecord(BaseModel):
    """Gerrit included-in record."""

    change_id: str | None = None
    change_number: int | None = None
    branches: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    raw: dict[str, Any] | None = None


class ReleaseReadinessReport(BaseModel):
    """Cross-system release readiness report."""

    project_key: str
    version_name: str
    jira_issue_count: int = 0
    jira_unresolved_count: int = 0
    jira_blocker_count: int = 0
    gerrit_change_count: int = 0
    gerrit_open_change_count: int = 0
    gerrit_merged_change_count: int = 0
    unresolved_comment_count: int = 0
    negative_vote_count: int = 0
    missing_change_issue_links: list[str] = Field(default_factory=list)
    issues_without_gerrit_changes: list[str] = Field(default_factory=list)
    gerrit_changes_without_jira_issue: list[int] = Field(default_factory=list)
    graph: GraphResult | None = None
    warnings: list[str] = Field(default_factory=list)


class RiskSummary(BaseModel):
    """Deterministic heuristic risk summary, not an authoritative business decision."""

    risk_score: int = 0
    risk_level: str = "low"
    reasons: list[str] = Field(default_factory=list)
    jira_issues: list[Any] = Field(default_factory=list)
    gerrit_changes: list[Any] = Field(default_factory=list)
    graph: GraphResult | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


def summarize_records(records: list[Any], *, group_by: str, key_getter: str) -> list[SummaryRecord]:
    """Group records by an attribute into generic summary records."""
    groups: dict[str, list[str]] = {}
    for record in records:
        key = str(getattr(record, key_getter, None) or "unassigned")
        issue_key = str(getattr(record, "issue_key", ""))
        groups.setdefault(key, []).append(issue_key)
    return [
        SummaryRecord(group_by=group_by, key=key, label=key, count=len(values), issue_keys=values)
        for key, values in sorted(groups.items())
    ]
