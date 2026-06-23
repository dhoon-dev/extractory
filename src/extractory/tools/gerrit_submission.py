"""Gerrit submission and included-in helpers."""

from __future__ import annotations

from extractory.gerrit.client import GerritClient
from extractory.tools.gerrit_graph import GerritChangeGraphTool
from extractory.tools.summaries import IncludedInRecord, SubmissionReadinessResult


def summarize_topic(client: GerritClient, topic: str) -> list[object]:
    """Return changes for a Gerrit topic."""
    return list(client.changes.query_all(f"topic:{topic}", option_preset="standard"))


def summarize_submitted_together(client: GerritClient, change_id: str) -> SubmissionReadinessResult:
    """Summarize Gerrit submitted-together data."""
    payload = client.changes.get_submitted_together(change_id)
    changes = payload.get("changes", []) if isinstance(payload.get("changes"), list) else []
    return SubmissionReadinessResult(
        root_change=change_id,
        submitted_together_changes=changes,
        non_visible_changes=int(payload.get("non_visible_changes") or 0),
        submittable_count=sum(
            bool(change.get("submittable")) for change in changes if isinstance(change, dict)
        ),
        not_submittable_count=sum(
            not bool(change.get("submittable")) for change in changes if isinstance(change, dict)
        ),
        unresolved_comment_count=sum(
            int(change.get("unresolved_comment_count") or 0)
            for change in changes
            if isinstance(change, dict)
        ),
    )


def check_submission_readiness(client: GerritClient, change_id: str) -> SubmissionReadinessResult:
    """Check read-only submission readiness for one change."""
    result = summarize_submitted_together(client, change_id)
    result.graph = GerritChangeGraphTool(client).crawl_related_changes(
        [change_id],
        include_submitted_together=True,
        include_related=False,
    )
    return result


def get_included_in(client: GerritClient, change_id: str) -> IncludedInRecord:
    """Return branches and tags containing a Gerrit change."""
    payload = client.changes.get_included_in(change_id)
    return IncludedInRecord(
        change_id=change_id,
        branches=payload.get("branches", []) if isinstance(payload.get("branches"), list) else [],
        tags=payload.get("tags", []) if isinstance(payload.get("tags"), list) else [],
        raw=payload,
    )


def summarize_merged_locations(client: GerritClient, change_id: str) -> IncludedInRecord:
    """Alias for included-in summary."""
    return get_included_in(client, change_id)
