"""Jira normalization."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from extractory.jira.fields import JiraFieldCatalog
from extractory.jira.records import JiraIssueRecord
from extractory.normalization.builtins import (
    JiraIssueLinksNormalizer,
    parse_date,
    parse_datetime,
)
from extractory.normalization.context import (
    FieldNormalizationContext,
    FieldNormalizationResult,
)
from extractory.normalization.registry import (
    ConflictPolicy,
    ErrorPolicy,
    FieldNormalizerRegistry,
    call_normalizer,
    merge_value,
)
from extractory.normalization.result import NormalizationResult


def _named(value: Any) -> tuple[str | None, str | None]:
    if isinstance(value, dict):
        return (
            value.get("name") or value.get("value") or value.get("displayName"),
            value.get("id") or value.get("key"),
        )
    return None, None


def _user_outputs(output_key_prefix: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {
            output_key_prefix: None,
            f"{output_key_prefix}_name": None,
            f"{output_key_prefix}_key": None,
            f"{output_key_prefix}_display_name": None,
            f"{output_key_prefix}_email": None,
        }
    return {
        output_key_prefix: value.get("displayName") or value.get("name") or value.get("key"),
        f"{output_key_prefix}_name": value.get("name"),
        f"{output_key_prefix}_key": value.get("key"),
        f"{output_key_prefix}_display_name": value.get("displayName"),
        f"{output_key_prefix}_email": value.get("emailAddress"),
    }


def _names(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for value in values:
        name, _identifier = _named(value)
        if name is not None:
            result.append(name)
    return result


def _raw_payload(entity: Mapping[str, Any]) -> dict[str, Any]:
    raw = entity.get("raw")
    if isinstance(raw, Mapping):
        nested = raw.get("raw")
        return dict(nested) if isinstance(nested, Mapping) else dict(raw)
    return dict(entity)


def _set_if_present(
    target: dict[str, Any], key: str, source: Mapping[str, Any], field_id: str
) -> None:
    if field_id in source:
        target[key] = source.get(field_id)


class _JiraStandardFieldNormalizer:
    """Default normalizer for built-in Jira fields."""

    def __init__(self, field_id: str) -> None:
        self.field_id = field_id

    def __call__(
        self,
        value: Any,
        context: FieldNormalizationContext,
    ) -> FieldNormalizationResult:
        """Normalize a standard Jira field into Extractory's built-in output keys."""
        del context
        outputs: dict[str, Any] = {}
        match self.field_id:
            case "project":
                outputs.update(
                    {
                        "project": value.get("name") if isinstance(value, Mapping) else None,
                        "project_id": value.get("id") if isinstance(value, Mapping) else None,
                        "project_key": value.get("key") if isinstance(value, Mapping) else None,
                    }
                )
            case "issuetype":
                outputs.update(
                    {
                        "issuetype": value.get("name") if isinstance(value, Mapping) else None,
                        "issuetype_id": value.get("id") if isinstance(value, Mapping) else None,
                    }
                )
            case "summary":
                outputs["summary"] = value
            case "description":
                outputs["description"] = value
            case "status":
                status_category = (
                    value.get("statusCategory", {}) if isinstance(value, Mapping) else {}
                )
                outputs.update(
                    {
                        "status": value.get("name") if isinstance(value, Mapping) else None,
                        "status_id": value.get("id") if isinstance(value, Mapping) else None,
                        "status_category": status_category.get("name")
                        if isinstance(status_category, Mapping)
                        else None,
                        "status_category_key": status_category.get("key")
                        if isinstance(status_category, Mapping)
                        else None,
                    }
                )
            case "priority":
                outputs.update(
                    {
                        "priority": value.get("name") if isinstance(value, Mapping) else None,
                        "priority_id": value.get("id") if isinstance(value, Mapping) else None,
                    }
                )
            case "resolution":
                outputs.update(
                    {
                        "resolution": value.get("name") if isinstance(value, Mapping) else None,
                        "resolution_id": value.get("id") if isinstance(value, Mapping) else None,
                    }
                )
            case "assignee" | "reporter" | "creator":
                outputs.update(_user_outputs(self.field_id, value))
            case "labels":
                outputs["labels"] = (
                    [str(label) for label in value] if isinstance(value, list) else []
                )
            case "components":
                outputs["components"] = _names(value)
            case "fixVersions":
                outputs["fixVersions"] = _names(value)
            case "versions":
                outputs["versions"] = _names(value)
            case "created":
                outputs["created"] = parse_datetime(value)
            case "updated":
                outputs["updated"] = parse_datetime(value)
            case "resolutiondate":
                outputs["resolutiondate"] = parse_datetime(value)
            case "duedate":
                outputs["duedate"] = parse_date(value)
            case _:
                return FieldNormalizationResult(raw_value=value, normalized=False)
        return FieldNormalizationResult(outputs=outputs, raw_value=value, normalized=True)


def _default_normalizer_for_field(field_id: str) -> Any | None:
    if field_id == "issuelinks":
        return JiraIssueLinksNormalizer()
    if field_id in _STANDARD_FIELD_IDS:
        return _JiraStandardFieldNormalizer(field_id)
    return None


_STANDARD_FIELD_IDS = {
    "summary",
    "description",
    "status",
    "issuetype",
    "project",
    "priority",
    "resolution",
    "assignee",
    "reporter",
    "creator",
    "labels",
    "components",
    "fixVersions",
    "versions",
    "created",
    "updated",
    "resolutiondate",
    "duedate",
}


def normalize_jira_issue(
    issue: Mapping[str, Any],
    *,
    field_map: Mapping[str, str] | None = None,
    field_catalog: JiraFieldCatalog | None = None,
    normalizers: FieldNormalizerRegistry | None = None,
    include_raw: bool = True,
    conflict_policy: ConflictPolicy = "raise",
    error_policy: ErrorPolicy = "keep_raw",
) -> NormalizationResult[JiraIssueRecord]:
    """Normalize one Jira issue mapping into an analytics-friendly record."""
    raw_payload = _raw_payload(issue)
    fields = issue.get("fields", {})
    if not isinstance(fields, Mapping):
        fields = {}
    record_data: dict[str, Any] = {
        "source": "jira",
        "issue_key": issue.get("key") or "",
    }
    if include_raw:
        record_data["raw"] = raw_payload
    _set_if_present(record_data, "issue_id", issue, "id")
    _set_if_present(record_data, "self_url", issue, "self")

    registry = normalizers or FieldNormalizerRegistry()
    aliases_by_field = {field_id: alias for alias, field_id in (field_map or {}).items()}
    warnings: list[str] = []
    child_records: list[Any] = []
    custom: dict[str, Any] = {}
    for field_id, value in fields.items():
        field = field_catalog.by_id(field_id) if field_catalog else None
        schema = field.schema_ if field else None
        field_name = field.name if field else None
        alias = aliases_by_field.get(field_id)
        context = FieldNormalizationContext(
            source="jira",
            entity_type="issue",
            field_id=field_id,
            field_name=field_name,
            field_alias=alias,
            schema_type=schema.get("type") if isinstance(schema, Mapping) else None,
            schema_items=schema.get("items") if isinstance(schema, Mapping) else None,
            schema_custom=schema.get("custom") if isinstance(schema, Mapping) else None,
            issue_key=str(issue.get("key") or ""),
            field_catalog=field_catalog,
            raw_entity=raw_payload,
        )
        normalizer = registry.resolve(
            context,
            default=_default_normalizer_for_field(field_id),
        )
        result = call_normalizer(normalizer, value, context, error_policy=error_policy)
        warnings.extend(result.warnings)
        child_records.extend(result.child_records)
        for key, output_value in result.outputs.items():
            merge_value(record_data, key, output_value, policy=conflict_policy)
        for key, custom_value in result.custom.items():
            merge_value(custom, key, custom_value, policy="namespace", namespace=field_id)
    if custom:
        record_data["custom"] = custom
    if warnings:
        record_data["normalization_warnings"] = warnings
    record = JiraIssueRecord.model_validate(record_data)
    return NormalizationResult(record=record, child_records=child_records, warnings=warnings)
