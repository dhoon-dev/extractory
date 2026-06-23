"""Jira field catalog helpers."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field

from extractory.jira.models import JiraField


class JiraFieldCatalog(BaseModel):
    """Lookup structure for Jira fields by id and non-unique name."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    fields: list[JiraField] = Field(default_factory=list)

    @classmethod
    def from_payload(cls, payload: Iterable[dict[str, object]]) -> JiraFieldCatalog:
        """Build a field catalog from Jira `/field` response data."""
        return cls(fields=[JiraField.model_validate(item) for item in payload])

    def by_id(self, field_id: str) -> JiraField | None:
        """Return a field by stable Jira field id."""
        for field in self.fields:
            if field.id == field_id:
                return field
        return None

    def by_name(self, name: str) -> list[JiraField]:
        """Return fields with an exact display-name match."""
        return [field for field in self.fields if field.name == name]

    def names_index(self) -> dict[str, list[JiraField]]:
        """Return an index of non-unique field names."""
        index: defaultdict[str, list[JiraField]] = defaultdict(list)
        for field in self.fields:
            index[field.name].append(field)
        return dict(index)
