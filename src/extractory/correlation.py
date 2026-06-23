"""Issue-key extraction and Jira/Gerrit correlation helpers."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any, Literal

from extractory.records import IssueChangeLinkRecord

DEFAULT_ISSUE_KEY_REGEX = r"[A-Z][A-Z0-9]+-\d+"


def extract_issue_keys(text: object, *, pattern: str = DEFAULT_ISSUE_KEY_REGEX) -> list[str]:
    """Extract issue keys from text, preserving first-seen order."""
    if text is None:
        return []
    regex = re.compile(pattern)
    return list(dict.fromkeys(regex.findall(str(text))))


def _iter_strings(value: Any) -> Iterable[tuple[str, str]]:
    if value is None:
        return
    if isinstance(value, str):
        yield "value", value
    elif isinstance(value, Mapping):
        for key, child in value.items():
            for source, text in _iter_strings(child):
                yield f"{key}.{source}", text
    elif isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        for index, child in enumerate(value):
            for source, text in _iter_strings(child):
                yield f"{index}.{source}", text


def correlate_issue_keys(
    change: Mapping[str, Any],
    *,
    issue_key_regex: str = DEFAULT_ISSUE_KEY_REGEX,
) -> list[IssueChangeLinkRecord]:
    """Find Jira issue keys referenced by a Gerrit change payload."""
    source_values: list[tuple[str, object, Literal["high", "medium", "low"]]] = [
        ("topic", change.get("topic"), "high"),
        ("subject", change.get("subject"), "high"),
        ("hashtags", change.get("hashtags"), "medium"),
        ("tracking_ids", change.get("tracking_ids"), "high"),
        ("custom_keyed_values", change.get("custom_keyed_values"), "low"),
        ("messages", change.get("messages"), "medium"),
        ("revisions", change.get("revisions"), "medium"),
    ]
    records: list[IssueChangeLinkRecord] = []
    seen: set[tuple[str, str]] = set()
    for match_source, value, confidence in source_values:
        for nested_source, text in _iter_strings(value):
            source = match_source if nested_source == "value" else f"{match_source}.{nested_source}"
            for issue_key in extract_issue_keys(text, pattern=issue_key_regex):
                key = (issue_key, source)
                if key in seen:
                    continue
                seen.add(key)
                records.append(
                    IssueChangeLinkRecord(
                        issue_key=issue_key,
                        change_id=str(change.get("id")) if change.get("id") is not None else None,
                        change_number=change.get("_number"),
                        project=change.get("project"),
                        branch=change.get("branch"),
                        topic=change.get("topic"),
                        subject=change.get("subject"),
                        match_source=source,
                        confidence=confidence,
                        raw=dict(change),
                    )
                )
    return records
