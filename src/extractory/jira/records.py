"""Analytics-friendly Jira record models."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import Field

from extractory.records import AnalyticsRecord


class JiraIssueRecord(AnalyticsRecord):
    """Normalized Jira issue record."""

    source: Literal["jira"] = "jira"
    issue_id: str | None = None
    issue_key: str
    self_url: str | None = None
    project: str | None = None
    project_id: str | None = None
    project_key: str | None = None
    issuetype: str | None = None
    issuetype_id: str | None = None
    summary: str | None = None
    description: str | None = None
    status: str | None = None
    status_id: str | None = None
    status_category: str | None = None
    status_category_key: str | None = None
    priority: str | None = None
    priority_id: str | None = None
    resolution: str | None = None
    resolution_id: str | None = None
    assignee: str | None = None
    assignee_name: str | None = None
    assignee_key: str | None = None
    assignee_display_name: str | None = None
    assignee_email: str | None = None
    reporter: str | None = None
    reporter_name: str | None = None
    reporter_key: str | None = None
    reporter_display_name: str | None = None
    reporter_email: str | None = None
    creator: str | None = None
    creator_name: str | None = None
    creator_key: str | None = None
    creator_display_name: str | None = None
    creator_email: str | None = None
    labels: list[str] = Field(default_factory=list)
    components: list[str] = Field(default_factory=list)
    versions: list[str] = Field(default_factory=list)
    created: datetime | None = None
    updated: datetime | None = None
    resolutiondate: datetime | None = None
    duedate: date | None = None
    story_points: float | None = None
    epic_key: str | None = None
    sprint_ids: list[int] = Field(default_factory=list)
    sprint_names: list[str] = Field(default_factory=list)
    sprint_states: list[str] = Field(default_factory=list)
    active_sprint_names: list[str] = Field(default_factory=list)
    latest_sprint_name: str | None = None
    custom: dict[str, Any] = Field(default_factory=dict)
    normalization_warnings: list[str] = Field(default_factory=list)
    raw: dict[str, Any] | None = None


class JiraCommentRecord(AnalyticsRecord):
    """Normalized Jira comment record."""

    source: Literal["jira"] = "jira"
    issue_key: str
    comment_id: str | None = None
    author_key: str | None = None
    author_name: str | None = None
    author_display_name: str | None = None
    author_email: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    body_text: str | None = None
    raw: dict[str, Any] | None = None


class JiraChangelogRecord(AnalyticsRecord):
    """Normalized Jira changelog item record."""

    source: Literal["jira"] = "jira"
    issue_key: str
    history_id: str | None = None
    author_key: str | None = None
    author_name: str | None = None
    author_display_name: str | None = None
    created_at: datetime | None = None
    field: str | None = None
    field_type: str | None = None
    from_value: str | None = None
    from_string: str | None = None
    to_value: str | None = None
    to_string: str | None = None
    raw: dict[str, Any] | None = None


class JiraIssueLinkRecord(AnalyticsRecord):
    """Normalized Jira issue link record."""

    source: Literal["jira"] = "jira"
    issue_key: str
    linked_issue_key: str
    link_type: str | None = None
    direction: Literal["inward", "outward", "unknown"] = "unknown"
    linked_issue_id: str | None = None
    linked_issue_status: str | None = None
    linked_issue_summary: str | None = None
    raw: dict[str, Any] | None = None


class JiraSprintRecord(AnalyticsRecord):
    """Normalized Jira Agile sprint record."""

    source: Literal["jira"] = "jira"
    issue_key: str | None = None
    sprint_id: int | None = None
    sprint_name: str | None = None
    sprint_state: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    complete_at: datetime | None = None
    raw: dict[str, Any] | str | None = None
