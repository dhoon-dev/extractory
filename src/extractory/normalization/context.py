"""Normalization context models and protocols."""

from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field


class FieldNormalizationContext(BaseModel):
    """Context passed to field normalizer callables."""

    source: Literal["jira", "gerrit"]
    entity_type: str
    field_id: str | None = None
    field_name: str | None = None
    field_alias: str | None = None
    schema_type: str | None = None
    schema_items: str | None = None
    schema_custom: str | None = None
    issue_key: str | None = None
    change_number: int | None = None
    path: tuple[str, ...] = ()
    field_catalog: Any | None = None
    raw_entity: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class FieldNormalizationResult(BaseModel):
    """Result returned by one field normalizer."""

    outputs: dict[str, Any] = Field(default_factory=dict)
    custom: dict[str, Any] = Field(default_factory=dict)
    child_records: list[Any] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    raw_value: Any = None
    normalized: bool = False


class FieldNormalizer(Protocol):
    """Callable normalizer protocol."""

    def __call__(
        self,
        value: Any,
        context: FieldNormalizationContext,
    ) -> FieldNormalizationResult:
        """Normalize a source field value."""
