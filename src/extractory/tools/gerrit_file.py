"""Gerrit file impact helpers."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from extractory.gerrit.client import GerritClient
from extractory.tools.summaries import GerritFileImpactRecord


def collect_changed_files(client: GerritClient, change_id: str) -> dict[str, object]:
    """Collect changed files for one Gerrit change."""
    return client.changes.get_files(change_id)


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def summarize_file_impact(
    client: GerritClient,
    query_or_changes: str,
) -> list[GerritFileImpactRecord]:
    """Summarize file impact for a Gerrit query."""
    files: dict[str, GerritFileImpactRecord] = {}
    for change in client.changes.query_all(query_or_changes, option_preset="files"):
        raw = change.raw or change.model_dump(by_alias=True)
        revisions = _mapping(raw.get("revisions"))
        for revision in revisions.values():
            if not isinstance(revision, dict):
                continue
            revision_files = _mapping(revision.get("files"))
            for path, file_info in revision_files.items():
                if not isinstance(file_info, dict):
                    continue
                record = files.setdefault(
                    str(path),
                    GerritFileImpactRecord(
                        file_path=str(path),
                        project=raw.get("project"),
                        branch=raw.get("branch"),
                    ),
                )
                if change.change_number not in record.changes:
                    record.changes.append(change.change_number)
                record.change_count = len(record.changes)
                record.total_insertions += int(file_info.get("lines_inserted") or 0)
                record.total_deletions += int(file_info.get("lines_deleted") or 0)
    return list(files.values())


def find_changes_touching_paths(
    client: GerritClient,
    paths: list[str],
    *,
    query_base: str | None = None,
) -> dict[str, list[int]]:
    """Find changes touching one or more file paths."""
    result: defaultdict[str, list[int]] = defaultdict(list)
    for path in paths:
        query = f"{query_base or ''} file:{path}".strip()
        for change in client.changes.query_all(query, option_preset="minimal"):
            result[path].append(change.change_number)
    return dict(result)
