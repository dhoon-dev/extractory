"""Convenience Jira extraction helpers."""

from __future__ import annotations

from collections.abc import Iterable

from extractory.jira.models import JiraIssue


def issue_keys(issues: Iterable[JiraIssue]) -> list[str]:
    """Return issue keys from Jira issue models."""
    return [issue.key for issue in issues]
