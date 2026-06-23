"""Convenience Gerrit extraction helpers."""

from __future__ import annotations

from collections.abc import Iterable

from extractory.gerrit.models import GerritChangeInfo


def change_numbers(changes: Iterable[GerritChangeInfo]) -> list[int]:
    """Return Gerrit change numbers."""
    return [change.change_number for change in changes]
