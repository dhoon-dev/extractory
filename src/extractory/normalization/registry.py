"""Callable-first field normalizer registry."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal, cast

from extractory.normalization.builtins import RawJsonNormalizer, generic_normalizer_for_schema
from extractory.normalization.context import (
    FieldNormalizationContext,
    FieldNormalizationResult,
    FieldNormalizer,
)

ConflictPolicy = Literal["raise", "keep_first", "keep_last", "append", "namespace"]
ErrorPolicy = Literal["raise", "warn", "keep_raw", "null"]


class FieldNormalizerRegistry:
    """Resolve normalizer callables by deterministic priority."""

    def __init__(self, *, enable_field_name_matching: bool = False) -> None:
        self.enable_field_name_matching = enable_field_name_matching
        self._field_ids: dict[str, FieldNormalizer] = {}
        self._aliases: dict[str, FieldNormalizer] = {}
        self._field_names: dict[str, FieldNormalizer] = {}
        self._jira_schemas: dict[tuple[str | None, str | None], FieldNormalizer] = {}
        self._gerrit_paths: dict[tuple[str, ...], FieldNormalizer] = {}
        self._fallback: FieldNormalizer = RawJsonNormalizer()

    def register_field_id(self, field_id: str, normalizer: FieldNormalizer) -> None:
        """Register a normalizer for one Jira field id."""
        self._field_ids[field_id] = normalizer

    def register_alias(self, alias: str, normalizer: FieldNormalizer) -> None:
        """Register a normalizer for an application field alias."""
        self._aliases[alias] = normalizer

    def register_field_name(self, name: str, normalizer: FieldNormalizer) -> None:
        """Register a Jira display-name normalizer."""
        self._field_names[name] = normalizer

    def register_jira_schema(
        self,
        *,
        type_: str | None,
        items: str | None = None,
        normalizer: FieldNormalizer,
    ) -> None:
        """Register a Jira schema-based normalizer."""
        self._jira_schemas[(type_, items)] = normalizer

    def register_gerrit_path(self, path: tuple[str, ...], normalizer: FieldNormalizer) -> None:
        """Register a Gerrit entity/path normalizer."""
        self._gerrit_paths[path] = normalizer

    def register_fallback(self, normalizer: FieldNormalizer) -> None:
        """Register the final raw-preserving fallback normalizer."""
        self._fallback = normalizer

    def resolve(
        self,
        context: FieldNormalizationContext,
        *,
        override: FieldNormalizer | None = None,
        default: FieldNormalizer | None = None,
    ) -> FieldNormalizer:
        """Resolve a normalizer using the v0 deterministic priority."""
        if override is not None:
            return override
        if context.field_id and context.field_id in self._field_ids:
            return self._field_ids[context.field_id]
        if context.field_alias and context.field_alias in self._aliases:
            return self._aliases[context.field_alias]
        if (
            self.enable_field_name_matching
            and context.field_name
            and context.field_name in self._field_names
        ):
            return self._field_names[context.field_name]
        if context.path and context.path in self._gerrit_paths:
            return self._gerrit_paths[context.path]
        schema_key = (context.schema_type, context.schema_items)
        if schema_key in self._jira_schemas:
            return self._jira_schemas[schema_key]
        if default is not None:
            return default
        generic = generic_normalizer_for_schema(context)
        if generic is not None:
            return cast("FieldNormalizer", generic)
        return self._fallback


def merge_value(
    target: dict[str, Any],
    key: str,
    value: Any,
    *,
    policy: ConflictPolicy,
    namespace: str | None = None,
) -> None:
    """Merge a normalized value into a target mapping."""
    final_key = f"{namespace}.{key}" if policy == "namespace" and namespace else key
    if final_key not in target:
        target[final_key] = value
        return
    if policy == "raise":
        raise ValueError(f"Conflicting normalized output key: {final_key}")
    if policy == "keep_first":
        return
    if policy == "keep_last":
        target[final_key] = value
        return
    if policy == "append":
        existing = target[final_key]
        if not isinstance(existing, list):
            existing = [existing]
        existing.append(value)
        target[final_key] = existing
        return
    if policy == "namespace":
        target[final_key] = value


def call_normalizer(
    normalizer: FieldNormalizer,
    value: Any,
    context: FieldNormalizationContext,
    *,
    error_policy: ErrorPolicy,
) -> FieldNormalizationResult:
    """Call a normalizer and apply the selected error policy."""
    try:
        return normalizer(value, context)
    except Exception as exc:
        if error_policy == "raise":
            raise
        warning = (
            f"Normalizer failed for {context.field_id or context.path or context.field_alias}: "
            f"{type(exc).__name__}"
        )
        if error_policy == "null":
            return FieldNormalizationResult(
                outputs={context.field_alias or context.field_id or "value": None},
                warnings=[warning],
                raw_value=value,
                normalized=True,
            )
        if error_policy == "warn":
            return FieldNormalizationResult(warnings=[warning], raw_value=value, normalized=False)
        return FieldNormalizationResult(
            custom={context.field_alias or context.field_id or "raw": value},
            warnings=[warning],
            raw_value=value,
            normalized=False,
        )


def make_function_normalizer(
    function: Callable[[Any, FieldNormalizationContext], FieldNormalizationResult],
) -> FieldNormalizer:
    """Return a callable normalizer from a plain function."""
    return cast("FieldNormalizer", function)
