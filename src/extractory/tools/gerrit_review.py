"""Gerrit review health helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from extractory.gerrit.client import GerritClient
from extractory.gerrit.models import GerritChangeInfo
from extractory.normalization.builtins import parse_datetime
from extractory.tools.summaries import GerritReviewHealthRecord


def summarize_review_health(
    query_or_changes: str | list[GerritChangeInfo],
    *,
    client: GerritClient | None = None,
) -> list[GerritReviewHealthRecord]:
    """Summarize review health for a query or existing changes."""
    if isinstance(query_or_changes, str):
        if client is None:
            raise ValueError("client is required when query_or_changes is a query string")
        changes = list(client.changes.query_all(query_or_changes, option_preset="review"))
    else:
        changes = query_or_changes
    return [_review_health(change) for change in changes]


def _review_health(change: GerritChangeInfo) -> GerritReviewHealthRecord:
    raw = change.raw or change.model_dump(by_alias=True)
    created = parse_datetime(raw.get("created"))
    age_days = (datetime.now(UTC) - created).days if created is not None else None
    reviewers = _mapping(raw.get("reviewers"))
    reviewer_count = sum(len(value) for value in reviewers.values() if isinstance(value, list))
    labels = _mapping(raw.get("labels"))
    has_negative = any(
        _has_negative_vote(label) for label in labels.values() if isinstance(label, dict)
    )
    return GerritReviewHealthRecord(
        change_number=raw.get("_number"),
        change_id=raw.get("change_id"),
        project=raw.get("project"),
        branch=raw.get("branch"),
        topic=raw.get("topic"),
        subject=raw.get("subject"),
        status=raw.get("status"),
        owner=raw.get("owner", {}).get("name") if isinstance(raw.get("owner"), dict) else None,
        created_at=created,
        updated_at=parse_datetime(raw.get("updated")),
        age_days=age_days,
        unresolved_comment_count=raw.get("unresolved_comment_count"),
        total_comment_count=raw.get("total_comment_count"),
        insertions=raw.get("insertions"),
        deletions=raw.get("deletions"),
        label_summary=labels,
        submit_requirement_summary={
            item.get("name"): item.get("status")
            for item in raw.get("submit_requirements", [])
            if isinstance(item, dict)
        },
        reviewer_count=reviewer_count,
        missing_reviewers=reviewer_count == 0,
        has_negative_vote=has_negative,
        is_submittable=raw.get("submittable"),
        is_work_in_progress=bool(raw.get("work_in_progress")),
        raw=raw,
    )


def _has_negative_vote(label: dict[str, Any]) -> bool:
    if isinstance(label.get("rejected"), dict) or isinstance(label.get("disliked"), dict):
        return True
    value = label.get("value")
    return isinstance(value, int) and value < 0


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}
