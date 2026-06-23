"""Selective fetching models and request serialization helpers."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class FetchProfile(StrEnum):
    """Named fetch profiles for common data needs."""

    MINIMAL = "minimal"
    STANDARD = "standard"
    NORMALIZED = "normalized"
    GRAPH = "graph"
    DETAILED = "detailed"
    FULL = "full"


class JiraFieldSelection(BaseModel):
    """Jira field, expansion, and property selection."""

    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    expand: tuple[str, ...] = ()
    properties: tuple[str, ...] = ()
    include_raw: bool = True


class GerritOptionSelection(BaseModel):
    """Gerrit option and extra-endpoint selection."""

    options: tuple[object, ...] = ()
    include_comments: bool = False
    include_files: bool = False
    include_related: bool = False
    include_submitted_together: bool = False
    include_included_in: bool = False
    include_raw: bool = True


class DataRequirements(BaseModel):
    """Computed data needed by profiles, tools, and normalizers."""

    jira_fields: set[str] = Field(default_factory=set)
    jira_exclude_fields: set[str] = Field(default_factory=set)
    jira_expand: set[str] = Field(default_factory=set)
    jira_properties: set[str] = Field(default_factory=set)
    gerrit_options: set[object] = Field(default_factory=set)
    gerrit_extra_endpoints: set[str] = Field(default_factory=set)
    include_raw: bool = True

    def merged(self, other: DataRequirements) -> DataRequirements:
        """Return a deterministic additive merge."""
        return DataRequirements(
            jira_fields=self.jira_fields | other.jira_fields,
            jira_exclude_fields=self.jira_exclude_fields | other.jira_exclude_fields,
            jira_expand=self.jira_expand | other.jira_expand,
            jira_properties=self.jira_properties | other.jira_properties,
            gerrit_options=self.gerrit_options | other.gerrit_options,
            gerrit_extra_endpoints=self.gerrit_extra_endpoints | other.gerrit_extra_endpoints,
            include_raw=self.include_raw or other.include_raw,
        )


JIRA_PROFILE_FIELDS: dict[FetchProfile, tuple[str, ...]] = {
    FetchProfile.MINIMAL: ("summary", "status", "issuetype", "project", "updated"),
    FetchProfile.STANDARD: (
        "summary",
        "status",
        "issuetype",
        "project",
        "priority",
        "assignee",
        "reporter",
        "labels",
        "components",
        "fixVersions",
        "created",
        "updated",
    ),
    FetchProfile.NORMALIZED: (
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
    ),
    FetchProfile.GRAPH: (
        "summary",
        "status",
        "issuetype",
        "project",
        "priority",
        "assignee",
        "labels",
        "components",
        "fixVersions",
        "updated",
        "issuelinks",
        "parent",
        "subtasks",
    ),
    FetchProfile.DETAILED: ("*all",),
    FetchProfile.FULL: ("*all",),
}

JIRA_PROFILE_EXPAND: dict[FetchProfile, tuple[str, ...]] = {
    FetchProfile.MINIMAL: (),
    FetchProfile.STANDARD: (),
    FetchProfile.NORMALIZED: (),
    FetchProfile.GRAPH: (),
    FetchProfile.DETAILED: ("names", "schema"),
    FetchProfile.FULL: ("names", "schema", "changelog", "renderedFields"),
}


class GerritChangeOption(StrEnum):
    """Gerrit `o=` change query options."""

    LABELS = "LABELS"
    DETAILED_LABELS = "DETAILED_LABELS"
    SUBMIT_REQUIREMENTS = "SUBMIT_REQUIREMENTS"
    CURRENT_REVISION = "CURRENT_REVISION"
    ALL_REVISIONS = "ALL_REVISIONS"
    DOWNLOAD_COMMANDS = "DOWNLOAD_COMMANDS"
    CURRENT_COMMIT = "CURRENT_COMMIT"
    ALL_COMMITS = "ALL_COMMITS"
    CURRENT_FILES = "CURRENT_FILES"
    ALL_FILES = "ALL_FILES"
    DETAILED_ACCOUNTS = "DETAILED_ACCOUNTS"
    REVIEWER_UPDATES = "REVIEWER_UPDATES"
    MESSAGES = "MESSAGES"
    CURRENT_ACTIONS = "CURRENT_ACTIONS"
    CHANGE_ACTIONS = "CHANGE_ACTIONS"
    REVIEWED = "REVIEWED"
    SKIP_DIFFSTAT = "SKIP_DIFFSTAT"
    SUBMITTABLE = "SUBMITTABLE"
    WEB_LINKS = "WEB_LINKS"
    CHECK = "CHECK"
    COMMIT_FOOTERS = "COMMIT_FOOTERS"
    PUSH_CERTIFICATES = "PUSH_CERTIFICATES"
    TRACKING_IDS = "TRACKING_IDS"
    CUSTOM_KEYED_VALUES = "CUSTOM_KEYED_VALUES"
    STAR = "STAR"
    PARENTS = "PARENTS"


GERRIT_OPTION_PRESETS: dict[str, tuple[GerritChangeOption, ...]] = {
    "minimal": (GerritChangeOption.SKIP_DIFFSTAT,),
    "standard": (
        GerritChangeOption.LABELS,
        GerritChangeOption.CURRENT_REVISION,
        GerritChangeOption.DETAILED_ACCOUNTS,
    ),
    "review": (
        GerritChangeOption.DETAILED_LABELS,
        GerritChangeOption.DETAILED_ACCOUNTS,
        GerritChangeOption.SUBMIT_REQUIREMENTS,
        GerritChangeOption.MESSAGES,
        GerritChangeOption.REVIEWER_UPDATES,
        GerritChangeOption.SUBMITTABLE,
    ),
    "files": (GerritChangeOption.CURRENT_REVISION, GerritChangeOption.CURRENT_FILES),
    "commit": (
        GerritChangeOption.CURRENT_REVISION,
        GerritChangeOption.CURRENT_COMMIT,
        GerritChangeOption.COMMIT_FOOTERS,
    ),
    "graph": (
        GerritChangeOption.CURRENT_REVISION,
        GerritChangeOption.CURRENT_COMMIT,
        GerritChangeOption.DETAILED_ACCOUNTS,
        GerritChangeOption.TRACKING_IDS,
    ),
    "detailed": (
        GerritChangeOption.CURRENT_REVISION,
        GerritChangeOption.CURRENT_COMMIT,
        GerritChangeOption.CURRENT_FILES,
        GerritChangeOption.DETAILED_ACCOUNTS,
        GerritChangeOption.DETAILED_LABELS,
        GerritChangeOption.MESSAGES,
        GerritChangeOption.SUBMIT_REQUIREMENTS,
        GerritChangeOption.REVIEWER_UPDATES,
        GerritChangeOption.TRACKING_IDS,
        GerritChangeOption.CUSTOM_KEYED_VALUES,
    ),
    "full": (
        GerritChangeOption.ALL_REVISIONS,
        GerritChangeOption.ALL_COMMITS,
        GerritChangeOption.ALL_FILES,
        GerritChangeOption.DETAILED_ACCOUNTS,
        GerritChangeOption.DETAILED_LABELS,
        GerritChangeOption.MESSAGES,
        GerritChangeOption.SUBMIT_REQUIREMENTS,
        GerritChangeOption.REVIEWER_UPDATES,
        GerritChangeOption.TRACKING_IDS,
        GerritChangeOption.CUSTOM_KEYED_VALUES,
        GerritChangeOption.COMMIT_FOOTERS,
        GerritChangeOption.PARENTS,
    ),
}


def serialize_jira_fields(
    fields: tuple[str, ...] | list[str] | None,
    exclude_fields: tuple[str, ...] | list[str] | None = None,
) -> str | None:
    """Serialize Jira include and exclude field selections."""
    values: list[str] = []
    if fields:
        values.extend(fields)
    if exclude_fields:
        values.extend(field if field.startswith("-") else f"-{field}" for field in exclude_fields)
    return ",".join(dict.fromkeys(values)) if values else None


def serialize_csv(values: tuple[str, ...] | list[str] | None) -> str | None:
    """Serialize a string sequence as a comma-separated query value."""
    return ",".join(values) if values else None


def jira_profile_selection(
    profile: FetchProfile | str,
    *,
    field_map: dict[str, str] | None = None,
    include_changelog: bool = False,
) -> JiraFieldSelection:
    """Return Jira field selection for a fetch profile."""
    fetch_profile = FetchProfile(profile)
    fields = list(JIRA_PROFILE_FIELDS[fetch_profile])
    expand = list(JIRA_PROFILE_EXPAND[fetch_profile])
    if fetch_profile is FetchProfile.NORMALIZED and field_map:
        fields.extend(field_map.values())
    if include_changelog and "changelog" not in expand:
        expand.append("changelog")
    return JiraFieldSelection(
        include=tuple(dict.fromkeys(fields)),
        expand=tuple(dict.fromkeys(expand)),
    )


def normalize_gerrit_options(
    options: tuple[object, ...] | list[object] | None = None,
    *,
    option_preset: str | None = None,
    skip_diffstat: bool = False,
) -> tuple[GerritChangeOption, ...]:
    """Normalize Gerrit option objects and preset values into deterministic order."""
    normalized: list[GerritChangeOption] = []
    if option_preset:
        normalized.extend(GERRIT_OPTION_PRESETS[option_preset])
    if options:
        normalized.extend(
            option if isinstance(option, GerritChangeOption) else GerritChangeOption(str(option))
            for option in options
        )
    if skip_diffstat:
        normalized.append(GerritChangeOption.SKIP_DIFFSTAT)
    return tuple(dict.fromkeys(normalized))


def gerrit_options_params(options: tuple[GerritChangeOption, ...]) -> list[tuple[str, str]]:
    """Return repeated Gerrit `o=` query parameter pairs."""
    return [("o", option.value) for option in options]


def data_requirements_from_normalizer(normalizer: Any) -> DataRequirements:
    """Collect optional requirement declarations from a normalizer callable."""
    requirements = DataRequirements()
    for method_name, target in (
        ("required_jira_fields", requirements.jira_fields),
        ("required_jira_expand", requirements.jira_expand),
        ("required_gerrit_options", requirements.gerrit_options),
        ("required_gerrit_endpoints", requirements.gerrit_extra_endpoints),
    ):
        method = getattr(normalizer, method_name, None)
        if callable(method):
            target.update(method())
    return requirements
