"""Built-in normalization callables."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from extractory.correlation import extract_issue_keys
from extractory.jira.records import JiraIssueLinkRecord, JiraSprintRecord
from extractory.normalization.context import FieldNormalizationContext, FieldNormalizationResult


def parse_datetime(value: Any) -> datetime | None:
    """Parse Jira or Gerrit timestamp strings into timezone-aware datetimes when possible."""
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).replace("Z", "+00:00")
    if " " in text and "T" not in text:
        text = text.replace(" ", "T", 1)
    if "." in text:
        head, tail = text.split(".", 1)
        timezone_index = max(tail.find("+"), tail.find("-"))
        if timezone_index >= 0:
            fractional = tail[:timezone_index][:6]
            suffix = tail[timezone_index:]
            text = f"{head}.{fractional}{suffix}"
        else:
            text = f"{head}.{tail[:6]}"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.astimezone()


def parse_date(value: Any) -> date | None:
    """Parse an ISO date string."""
    if value in (None, ""):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _named(value: Any) -> tuple[str | None, str | None]:
    if isinstance(value, dict):
        return (
            value.get("name") or value.get("value") or value.get("displayName"),
            value.get("id") or value.get("key"),
        )
    if value is None:
        return None, None
    return str(value), None


def _array_names(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    names: list[str] = []
    for item in value:
        name, _identifier = _named(item)
        if name is not None:
            names.append(name)
    return names


class IdentityNormalizer:
    """Return a value unchanged under the requested column name."""

    def __init__(self, column: str | None = None) -> None:
        self.column = column

    def __call__(self, value: Any, context: FieldNormalizationContext) -> FieldNormalizationResult:
        """Normalize by preserving the original value."""
        column = self.column or context.field_alias or context.field_id or "value"
        return FieldNormalizationResult(
            columns={column: value},
            raw_value=value,
            normalized=True,
        )


class StringNormalizer(IdentityNormalizer):
    """Normalize a value to string."""

    def __call__(self, value: Any, context: FieldNormalizationContext) -> FieldNormalizationResult:
        """Normalize a value to string."""
        column = self.column or context.field_alias or context.field_id or "value"
        return FieldNormalizationResult(
            columns={column: None if value is None else str(value)},
            raw_value=value,
            normalized=True,
        )


class TextNormalizer(StringNormalizer):
    """Alias of string normalization for larger text fields."""


class DelimitedTextArrayNormalizer:
    """Split a text value into an array using a configured delimiter."""

    def __init__(
        self,
        delimiter: str,
        column: str | None = None,
        *,
        strip: bool = True,
        drop_empty: bool = True,
    ) -> None:
        if delimiter == "":
            raise ValueError("delimiter must not be empty")
        self.delimiter = delimiter
        self.column = column
        self.strip = strip
        self.drop_empty = drop_empty

    def __call__(self, value: Any, context: FieldNormalizationContext) -> FieldNormalizationResult:
        """Normalize delimited text to a string array."""
        column = self.column or context.field_alias or context.field_id or "values"
        if value in (None, ""):
            values: list[str] = []
        else:
            parts = str(value).split(self.delimiter)
            if self.strip:
                parts = [part.strip() for part in parts]
            values = [part for part in parts if part] if self.drop_empty else parts
        return FieldNormalizationResult(
            columns={column: values},
            raw_value=value,
            normalized=True,
        )


class NumberNormalizer(IdentityNormalizer):
    """Normalize a value to float."""

    def __call__(self, value: Any, context: FieldNormalizationContext) -> FieldNormalizationResult:
        """Normalize a value to float."""
        column = self.column or context.field_alias or context.field_id or "value"
        parsed = None if value in (None, "") else float(value)
        return FieldNormalizationResult(columns={column: parsed}, raw_value=value, normalized=True)


class BooleanNormalizer(IdentityNormalizer):
    """Normalize a value to bool."""

    def __call__(self, value: Any, context: FieldNormalizationContext) -> FieldNormalizationResult:
        """Normalize a value to bool."""
        column = self.column or context.field_alias or context.field_id or "value"
        return FieldNormalizationResult(
            columns={column: None if value is None else bool(value)},
            raw_value=value,
            normalized=True,
        )


class DateNormalizer(IdentityNormalizer):
    """Normalize a value to date."""

    def __call__(self, value: Any, context: FieldNormalizationContext) -> FieldNormalizationResult:
        """Normalize a value to date."""
        column = self.column or context.field_alias or context.field_id or "value"
        return FieldNormalizationResult(
            columns={column: parse_date(value)},
            raw_value=value,
            normalized=True,
        )


class DatetimeNormalizer(IdentityNormalizer):
    """Normalize a value to datetime."""

    def __call__(self, value: Any, context: FieldNormalizationContext) -> FieldNormalizationResult:
        """Normalize a value to datetime."""
        column = self.column or context.field_alias or context.field_id or "value"
        return FieldNormalizationResult(
            columns={column: parse_datetime(value)},
            raw_value=value,
            normalized=True,
        )


class JiraUserNormalizer:
    """Normalize Jira on-prem user objects."""

    def __init__(self, prefix: str | None = None) -> None:
        self.prefix = prefix

    def __call__(self, value: Any, context: FieldNormalizationContext) -> FieldNormalizationResult:
        """Normalize user object columns."""
        prefix = self.prefix or context.field_alias or context.field_id or "user"
        if not isinstance(value, dict):
            return FieldNormalizationResult(raw_value=value, normalized=False)
        return FieldNormalizationResult(
            columns={
                f"{prefix}_name": value.get("name"),
                f"{prefix}_key": value.get("key"),
                f"{prefix}_display_name": value.get("displayName"),
                f"{prefix}_email": value.get("emailAddress"),
            },
            raw_value=value,
            normalized=True,
        )


class JiraUserArrayNormalizer:
    """Normalize arrays of Jira users."""

    def __init__(self, column: str | None = None) -> None:
        self.column = column

    def __call__(self, value: Any, context: FieldNormalizationContext) -> FieldNormalizationResult:
        """Normalize user arrays to display names."""
        column = self.column or context.field_alias or context.field_id or "users"
        users = value if isinstance(value, list) else []
        names = [user.get("displayName") for user in users if isinstance(user, dict)]
        return FieldNormalizationResult(columns={column: names}, raw_value=value, normalized=True)


class NamedObjectNormalizer:
    """Normalize a named object into name and id columns."""

    def __init__(self, column: str | None = None) -> None:
        self.column = column

    def __call__(self, value: Any, context: FieldNormalizationContext) -> FieldNormalizationResult:
        """Normalize a Jira named object."""
        column = self.column or context.field_alias or context.field_id or "value"
        name, identifier = _named(value)
        return FieldNormalizationResult(
            columns={column: name, f"{column}_id": identifier},
            raw_value=value,
            normalized=True,
        )


class NamedArrayNormalizer:
    """Normalize an array of named objects to names."""

    def __init__(self, column: str | None = None) -> None:
        self.column = column

    def __call__(self, value: Any, context: FieldNormalizationContext) -> FieldNormalizationResult:
        """Normalize a named array."""
        column = self.column or context.field_alias or context.field_id or "values"
        return FieldNormalizationResult(
            columns={column: _array_names(value)},
            raw_value=value,
            normalized=True,
        )


class OptionNormalizer(NamedObjectNormalizer):
    """Normalize a Jira option object."""


class OptionArrayNormalizer(NamedArrayNormalizer):
    """Normalize a Jira option array."""


class LabelsNormalizer:
    """Normalize Jira labels."""

    def __init__(self, column: str = "labels") -> None:
        self.column = column

    def __call__(self, value: Any, context: FieldNormalizationContext) -> FieldNormalizationResult:
        """Normalize labels to strings."""
        del context
        labels = [str(item) for item in value] if isinstance(value, list) else []
        return FieldNormalizationResult(
            columns={self.column: labels},
            raw_value=value,
            normalized=True,
        )


class VersionArrayNormalizer(NamedArrayNormalizer):
    """Normalize Jira version arrays."""


class ComponentArrayNormalizer(NamedArrayNormalizer):
    """Normalize Jira component arrays."""


class CascadingSelectNormalizer:
    """Normalize Jira cascading select fields."""

    def __init__(self, column: str | None = None) -> None:
        self.column = column

    def __call__(self, value: Any, context: FieldNormalizationContext) -> FieldNormalizationResult:
        """Normalize parent and child option path."""
        column = self.column or context.field_alias or context.field_id or "cascading"
        if not isinstance(value, dict):
            return FieldNormalizationResult(raw_value=value, normalized=False)
        parent = value.get("value")
        child = (
            value.get("child", {}).get("value") if isinstance(value.get("child"), dict) else None
        )
        path = [item for item in (parent, child) if item]
        return FieldNormalizationResult(
            columns={f"{column}_parent": parent, f"{column}_child": child, f"{column}_path": path},
            raw_value=value,
            normalized=True,
        )


class JiraSprintNormalizer:
    """Normalize Jira Agile sprint custom field values."""

    def __init__(
        self,
        *,
        names_column: str = "sprint_names",
        active_names_column: str = "active_sprint_names",
        latest_name_column: str = "latest_sprint_name",
        emit_child_records: bool = False,
    ) -> None:
        self.names_column = names_column
        self.active_names_column = active_names_column
        self.latest_name_column = latest_name_column
        self.emit_child_records = emit_child_records

    def required_jira_fields(self) -> set[str]:
        """Return no hard-coded field ids; callers provide the target field."""
        return set()

    def __call__(self, value: Any, context: FieldNormalizationContext) -> FieldNormalizationResult:
        """Normalize sprint strings or objects into analytics columns."""
        del context
        items = value if isinstance(value, list) else ([] if value is None else [value])
        sprints = [self._parse_sprint(item) for item in items]
        sprint_ids = [sprint.sprint_id for sprint in sprints if sprint.sprint_id is not None]
        sprint_names = [sprint.sprint_name for sprint in sprints if sprint.sprint_name is not None]
        sprint_states = [
            sprint.sprint_state for sprint in sprints if sprint.sprint_state is not None
        ]
        active_names = [
            sprint.sprint_name
            for sprint in sprints
            if sprint.sprint_name is not None and (sprint.sprint_state or "").lower() == "active"
        ]
        return FieldNormalizationResult(
            columns={
                "sprint_ids": sprint_ids,
                self.names_column: sprint_names,
                "sprint_states": sprint_states,
                self.active_names_column: active_names,
                self.latest_name_column: sprint_names[-1] if sprint_names else None,
            },
            child_records=sprints if self.emit_child_records else [],
            raw_value=value,
            normalized=True,
        )

    def _parse_sprint(self, value: Any) -> JiraSprintRecord:
        if isinstance(value, dict):
            return JiraSprintRecord(
                sprint_id=self._to_int(value.get("id")),
                sprint_name=value.get("name"),
                sprint_state=value.get("state"),
                start_at=parse_datetime(value.get("startDate") or value.get("start_at")),
                end_at=parse_datetime(value.get("endDate") or value.get("end_at")),
                complete_at=parse_datetime(value.get("completeDate") or value.get("complete_at")),
                raw=value,
            )
        text = str(value)
        data = dict(re.findall(r"([A-Za-z]+)=([^,\]]+)", text))
        return JiraSprintRecord(
            sprint_id=self._to_int(data.get("id")),
            sprint_name=data.get("name"),
            sprint_state=data.get("state"),
            start_at=parse_datetime(data.get("startDate")),
            end_at=parse_datetime(data.get("endDate")),
            complete_at=parse_datetime(data.get("completeDate")),
            raw=text,
        )

    @staticmethod
    def _to_int(value: Any) -> int | None:
        try:
            return None if value in (None, "") else int(value)
        except (TypeError, ValueError):
            return None


class RawJsonNormalizer:
    """Preserve a value in custom raw JSON output."""

    def __call__(self, value: Any, context: FieldNormalizationContext) -> FieldNormalizationResult:
        """Preserve the raw value under field alias or id."""
        key = context.field_alias or context.field_id or ".".join(context.path) or "raw"
        return FieldNormalizationResult(
            custom={key: value},
            raw_value=value,
            normalized=False,
        )


class RegexExtractNormalizer:
    """Extract regex groups into columns."""

    def __init__(self, *, pattern: str, columns: dict[str, str]) -> None:
        self.pattern = re.compile(pattern)
        self.columns = columns

    def __call__(self, value: Any, context: FieldNormalizationContext) -> FieldNormalizationResult:
        """Extract regex matches from text."""
        del context
        text = "" if value is None else str(value)
        match = self.pattern.search(text)
        columns: dict[str, Any] = {}
        if match:
            for source, target in self.columns.items():
                if source.startswith("group_"):
                    index = int(source.removeprefix("group_"))
                    columns[target] = match.group(index)
                else:
                    columns[target] = match.group(source)
        return FieldNormalizationResult(columns=columns, raw_value=value, normalized=bool(match))


class IssueKeyExtractNormalizer:
    """Extract issue keys from arbitrary text."""

    def __init__(self, *, pattern: str, column: str = "issue_keys") -> None:
        self.pattern = pattern
        self.column = column

    def __call__(self, value: Any, context: FieldNormalizationContext) -> FieldNormalizationResult:
        """Extract issue keys."""
        del context
        return FieldNormalizationResult(
            columns={self.column: extract_issue_keys(value, pattern=self.pattern)},
            raw_value=value,
            normalized=True,
        )


class JiraIssueLinksNormalizer:
    """Normalize Jira issue links into child records."""

    def __call__(self, value: Any, context: FieldNormalizationContext) -> FieldNormalizationResult:
        """Emit Jira issue link child records."""
        records: list[JiraIssueLinkRecord] = []
        links = value if isinstance(value, list) else []
        for link in links:
            if not isinstance(link, dict):
                continue
            link_type = link.get("type", {})
            for direction, issue_key in (("outward", "outwardIssue"), ("inward", "inwardIssue")):
                linked = link.get(issue_key)
                if not isinstance(linked, dict):
                    continue
                fields = linked.get("fields", {})
                status = fields.get("status", {}) if isinstance(fields, dict) else {}
                records.append(
                    JiraIssueLinkRecord(
                        issue_key=context.issue_key or "",
                        linked_issue_key=linked.get("key") or "",
                        link_type=link_type.get("name") if isinstance(link_type, dict) else None,
                        direction=direction,
                        linked_issue_id=linked.get("id"),
                        linked_issue_status=status.get("name")
                        if isinstance(status, dict)
                        else None,
                        linked_issue_summary=fields.get("summary")
                        if isinstance(fields, dict)
                        else None,
                        raw=link,
                    )
                )
        return FieldNormalizationResult(child_records=records, raw_value=value, normalized=True)


def generic_normalizer_for_schema(
    context: FieldNormalizationContext,
) -> object | None:
    """Return a generic normalizer for a Jira schema context."""
    if context.schema_type == "string":
        return StringNormalizer(context.field_alias)
    if context.schema_type == "number":
        return NumberNormalizer(context.field_alias)
    if context.schema_type == "date":
        return DateNormalizer(context.field_alias)
    if context.schema_type == "datetime":
        return DatetimeNormalizer(context.field_alias)
    if context.schema_type == "user":
        return JiraUserNormalizer(context.field_alias)
    if context.schema_type == "array" and context.schema_items in {
        "option",
        "version",
        "component",
    }:
        return NamedArrayNormalizer(context.field_alias)
    if context.schema_type == "option":
        return OptionNormalizer(context.field_alias)
    return None
