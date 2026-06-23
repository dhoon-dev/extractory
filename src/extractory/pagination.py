"""Pagination helpers shared by Jira and Gerrit resources."""

from __future__ import annotations


def next_offset(start_at: int, returned_count: int) -> int:
    """Return the next offset and guard against non-advancing pagination."""
    if returned_count <= 0:
        return start_at
    return start_at + returned_count


def should_continue_offset_page(
    *,
    start_at: int,
    returned_count: int,
    total: int | None,
) -> bool:
    """Return whether an offset-paginated API should continue."""
    if returned_count <= 0:
        return False
    if total is None:
        return True
    return start_at + returned_count < total
