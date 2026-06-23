"""Typed-but-tolerant Jira API models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class JiraIssue(BaseModel):
    """Raw-ish Jira issue object returned by Jira REST API."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str | None = None
    key: str
    self_url: str | None = Field(default=None, alias="self")
    expand: str | None = None
    fields: dict[str, Any] = Field(default_factory=dict)
    names: dict[str, str] | None = None
    schema_: dict[str, Any] | None = Field(default=None, alias="schema")
    raw: dict[str, Any] | None = None


class JiraField(BaseModel):
    """Jira field catalog entry."""

    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    custom: bool | None = None
    orderable: bool | None = None
    navigable: bool | None = None
    searchable: bool | None = None
    clause_names: list[str] = Field(default_factory=list, alias="clauseNames")
    schema_: dict[str, Any] | None = Field(default=None, alias="schema")
