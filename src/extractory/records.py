"""Cross-system analytics records."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AnalyticsRecord(BaseModel):
    """Base model for analytics-friendly records."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Dump only values observed or explicitly set during normalization by default."""
        kwargs.setdefault("exclude_unset", True)
        return super().model_dump(**kwargs)

    def model_dump_json(self, **kwargs: Any) -> str:
        """Dump JSON using the same observed-value default as ``model_dump``."""
        kwargs.setdefault("exclude_unset", True)
        return super().model_dump_json(**kwargs)


class IssueChangeLinkRecord(AnalyticsRecord):
    """Correlation between a Jira issue key and a Gerrit change."""

    issue_key: str
    change_id: str | None = None
    change_number: int | None = None
    project: str | None = None
    branch: str | None = None
    topic: str | None = None
    subject: str | None = None
    match_source: str
    confidence: Literal["high", "medium", "low"] = "medium"
    raw: dict[str, Any] | None = None


class SummaryRecord(AnalyticsRecord):
    """Generic grouped summary record."""

    group_by: str
    key: str
    label: str | None = None
    count: int = 0
    issue_keys: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
