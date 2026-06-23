"""Typed-but-tolerant Gerrit API models and JSON parsing."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from extractory.exceptions import ErrorContext, GerritAPIError, sanitize_text

XSSI_PREFIX = ")]}'"


class GerritChangeInfo(BaseModel):
    """Raw-ish Gerrit ChangeInfo entity returned by Gerrit REST API."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str
    triplet_id: str | None = None
    project: str
    branch: str
    change_id: str
    subject: str
    status: str
    change_number: int = Field(alias="_number")
    topic: str | None = None
    created: str | None = None
    updated: str | None = None
    submitted: str | None = None
    owner: dict[str, Any] | None = None
    current_revision: str | None = None
    revisions: dict[str, Any] | None = None
    labels: dict[str, Any] | None = None
    reviewers: dict[str, Any] | None = None
    messages: list[dict[str, Any]] | None = None
    raw: dict[str, Any] | None = None


def strip_gerrit_xssi(text: str) -> str:
    """Strip Gerrit's XSSI protection prefix line."""
    stripped = text.lstrip()
    if stripped.startswith(XSSI_PREFIX):
        _, _, rest = stripped.partition("\n")
        return rest
    return text


def parse_gerrit_json_response(text: str) -> object:
    """Strip Gerrit XSSI prefix and parse JSON."""
    cleaned = strip_gerrit_xssi(text).strip()
    if cleaned == "":
        return None
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        context = ErrorContext(source="gerrit", response_body=sanitize_text(text))
        raise GerritAPIError("Invalid Gerrit JSON response", context=context) from exc


def change_info(payload: dict[str, Any], *, include_raw: bool = True) -> GerritChangeInfo:
    """Validate a Gerrit change payload and preserve raw JSON when requested."""
    if include_raw and "raw" not in payload:
        payload = {**payload, "raw": dict(payload)}
    if "triplet_id" not in payload and isinstance(payload.get("id"), str):
        payload = {**payload, "triplet_id": payload["id"]}
    return GerritChangeInfo.model_validate(payload)
