"""Normalization result container."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class NormalizationResult(BaseModel, Generic[T]):
    """Parent normalized record plus child records and warnings."""

    record: T
    child_records: list[Any] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
