import re
from typing import Any

import pytest

from extractory.jira.fields import JiraFieldCatalog
from extractory.normalization import (
    DelimitedTextArrayNormalizer,
    FieldNormalizationContext,
    FieldNormalizationResult,
    FieldNormalizerRegistry,
    JiraIssueLinksNormalizer,
    JiraSprintNormalizer,
    NumberNormalizer,
    TextNormalizer,
)
from extractory.normalization.jira import normalize_jira_issue


class WorkflowStatusNormalizer:
    def __call__(
        self,
        value: Any,
        context: FieldNormalizationContext,
    ) -> FieldNormalizationResult:
        del context
        status = value.get("name") if isinstance(value, dict) else value
        return FieldNormalizationResult(
            outputs={"workflow_status": None if status is None else str(status).lower()},
            raw_value=value,
            normalized=True,
        )


def test_jira_custom_field_map_and_sprint_normalization() -> None:
    registry = FieldNormalizerRegistry()
    registry.register_field_id("customfield_10016", NumberNormalizer(output_key="story_points"))
    registry.register_field_id("customfield_10020", JiraSprintNormalizer(emit_child_records=True))
    issue = {
        "id": "10001",
        "key": "ABC-1",
        "fields": {
            "summary": "Example",
            "customfield_10016": "3",
            "customfield_10020": [
                "com.atlassian.greenhopper.service.sprint.Sprint@1[id=7,state=ACTIVE,name=Sprint 7]"
            ],
        },
    }

    result = normalize_jira_issue(issue, normalizers=registry)

    assert result.record.story_points == 3.0
    assert result.record.sprint_ids == [7]
    assert result.record.latest_sprint_name == "Sprint 7"
    assert result.child_records


def test_unknown_custom_field_is_preserved() -> None:
    issue = {"key": "ABC-1", "fields": {"customfield_99999": {"plugin": "value"}}}

    result = normalize_jira_issue(issue)

    assert result.record.custom["customfield_99999.customfield_99999"] == {"plugin": "value"}


def test_field_catalog_schema_selects_generic_normalizer() -> None:
    catalog = JiraFieldCatalog.from_payload(
        [{"id": "customfield_10001", "name": "Text", "schema": {"type": "string"}}]
    )
    issue = {"key": "ABC-1", "fields": {"customfield_10001": "hello"}}

    result = normalize_jira_issue(
        issue, field_catalog=catalog, field_map={"text": "customfield_10001"}
    )

    assert result.record.model_extra is not None
    assert result.record.model_extra["text"] == "hello"


def test_model_dump_raw_wrapper_does_not_create_nested_raw() -> None:
    issue = {
        "key": "ABC-1",
        "fields": {"summary": "Example"},
        "raw": {"key": "ABC-1", "fields": {"summary": "Example"}},
    }

    result = normalize_jira_issue(issue)

    assert result.record.raw is not None
    assert "raw" not in result.record.raw


def test_unfetched_jira_fields_are_not_dumped_by_default() -> None:
    issue = {"key": "ABC-1", "fields": {"description": None}}

    result = normalize_jira_issue(issue, include_raw=False)
    dumped = result.record.model_dump()

    assert dumped == {
        "source": "jira",
        "issue_key": "ABC-1",
        "description": None,
    }
    assert "summary" not in dumped
    assert "status" not in dumped
    assert "labels" not in dumped


def test_full_schema_dump_is_still_available_when_requested() -> None:
    issue = {"key": "ABC-1", "fields": {"description": None}}

    result = normalize_jira_issue(issue, include_raw=False)
    dumped = result.record.model_dump(exclude_unset=False)

    assert dumped["summary"] is None
    assert dumped["labels"] == []


def test_builtin_scalar_field_can_use_custom_normalizer() -> None:
    registry = FieldNormalizerRegistry()
    registry.register_field_id("description", TextNormalizer(output_key="body"))
    issue = {"key": "ABC-1", "fields": {"description": "Hello"}}

    result = normalize_jira_issue(issue, normalizers=registry, include_raw=False)
    dumped = result.record.model_dump()

    assert dumped["body"] == "Hello"
    assert "description" not in dumped


def test_delimited_text_array_normalizer_splits_text_value() -> None:
    registry = FieldNormalizerRegistry()
    registry.register_field_id(
        "customfield_10030",
        DelimitedTextArrayNormalizer(delimiter=",", output_key="release_tags"),
    )
    issue = {"key": "ABC-1", "fields": {"customfield_10030": "alpha, beta,, gamma "}}

    result = normalize_jira_issue(issue, normalizers=registry, include_raw=False)
    dumped = result.record.model_dump()

    assert dumped["release_tags"] == ["alpha", "beta", "gamma"]


def test_delimited_text_array_normalizer_uses_whitespace_when_delimiter_is_omitted() -> None:
    registry = FieldNormalizerRegistry()
    registry.register_field_id(
        "customfield_10030",
        DelimitedTextArrayNormalizer(output_key="release_tags"),
    )
    issue = {"key": "ABC-1", "fields": {"customfield_10030": " alpha  beta\tgamma\n delta "}}

    result = normalize_jira_issue(issue, normalizers=registry, include_raw=False)
    dumped = result.record.model_dump()

    assert dumped["release_tags"] == ["alpha", "beta", "gamma", "delta"]


def test_delimited_text_array_normalizer_can_use_regex_delimiter() -> None:
    registry = FieldNormalizerRegistry()
    registry.register_field_id(
        "customfield_10030",
        DelimitedTextArrayNormalizer(
            delimiter=r"\s*[,;]\s*",
            output_key="release_tags",
            regex=True,
        ),
    )
    issue = {"key": "ABC-1", "fields": {"customfield_10030": "alpha, beta;gamma,, delta"}}

    result = normalize_jira_issue(issue, normalizers=registry, include_raw=False)
    dumped = result.record.model_dump()

    assert dumped["release_tags"] == ["alpha", "beta", "gamma", "delta"]


def test_delimited_text_array_normalizer_uses_literal_delimiters_by_default() -> None:
    registry = FieldNormalizerRegistry()
    registry.register_field_id(
        "customfield_10030",
        DelimitedTextArrayNormalizer(delimiter=r"\s+", output_key="release_tags"),
    )
    issue = {"key": "ABC-1", "fields": {"customfield_10030": r"alpha\s+beta gamma"}}

    result = normalize_jira_issue(issue, normalizers=registry, include_raw=False)
    dumped = result.record.model_dump()

    assert dumped["release_tags"] == ["alpha", "beta gamma"]


def test_delimited_text_array_normalizer_rejects_empty_delimiter() -> None:
    with pytest.raises(ValueError, match="delimiter"):
        DelimitedTextArrayNormalizer(delimiter="")


def test_delimited_text_array_normalizer_rejects_regex_without_delimiter() -> None:
    with pytest.raises(ValueError, match="regex delimiters require delimiter"):
        DelimitedTextArrayNormalizer(regex=True)


def test_delimited_text_array_normalizer_rejects_invalid_regex_delimiter() -> None:
    with pytest.raises(re.error):
        DelimitedTextArrayNormalizer(delimiter="[", regex=True)


def test_builtin_object_field_can_use_custom_normalizer() -> None:
    registry = FieldNormalizerRegistry()
    registry.register_field_id("status", WorkflowStatusNormalizer())
    issue = {"key": "ABC-1", "fields": {"status": {"id": "1", "name": "In Progress"}}}

    result = normalize_jira_issue(issue, normalizers=registry, include_raw=False)
    dumped = result.record.model_dump()

    assert dumped["workflow_status"] == "in progress"
    assert "status" not in dumped
    assert "status_id" not in dumped


def test_jira_issue_links_normalizer_emits_default_child_record_fields() -> None:
    link = {
        "id": "90001",
        "type": {"name": "Blocks", "outward": "blocks", "inward": "is blocked by"},
        "outwardIssue": {
            "id": "10002",
            "key": "ABC-2",
            "fields": {
                "summary": "Dependency",
                "status": {"name": "To Do"},
            },
        },
    }
    issue = {"key": "ABC-1", "fields": {"issuelinks": [link]}}

    result = normalize_jira_issue(issue, include_raw=False)

    assert len(result.child_records) == 1
    assert result.child_records[0].model_dump() == {
        "issue_key": "ABC-1",
        "linked_issue_key": "ABC-2",
        "link_type": "Blocks",
        "direction": "outward",
        "linked_issue_id": "10002",
        "linked_issue_status": "To Do",
        "linked_issue_summary": "Dependency",
        "raw": link,
    }


def test_jira_issue_links_normalizer_can_limit_child_record_fields() -> None:
    registry = FieldNormalizerRegistry()
    registry.register_field_id(
        "issuelinks",
        JiraIssueLinksNormalizer(
            include_fields=("linked_issue_key", "link_type", "direction"),
            include_raw=False,
        ),
    )
    issue = {
        "key": "ABC-1",
        "fields": {
            "issuelinks": [
                {
                    "type": {"name": "Relates"},
                    "inwardIssue": {
                        "id": "10003",
                        "key": "ABC-3",
                        "fields": {
                            "summary": "Related issue",
                            "status": {"name": "Done"},
                        },
                    },
                }
            ]
        },
    }

    result = normalize_jira_issue(issue, normalizers=registry, include_raw=False)

    assert len(result.child_records) == 1
    assert result.child_records[0].model_dump() == {
        "linked_issue_key": "ABC-3",
        "link_type": "Relates",
        "direction": "inward",
    }


def test_jira_issue_links_normalizer_rejects_unknown_child_record_fields() -> None:
    with pytest.raises(ValueError, match="unsupported Jira issue link field"):
        JiraIssueLinksNormalizer(include_fields=("linked_issue_key", "bogus"))


def test_standard_jira_fields_preserve_source_field_names() -> None:
    issue = {
        "key": "ABC-1",
        "fields": {
            "project": {"id": "10000", "key": "ABC", "name": "Example Project"},
            "issuetype": {"id": "1", "name": "Bug"},
            "summary": "Example",
            "description": "Hello",
            "status": {
                "id": "3",
                "name": "In Progress",
                "statusCategory": {"key": "indeterminate", "name": "In Progress"},
            },
            "priority": {"id": "2", "name": "Major"},
            "resolution": {"id": "1", "name": "Fixed"},
            "assignee": {
                "name": "alice",
                "key": "alice-key",
                "displayName": "Alice",
                "emailAddress": "alice@example.com",
            },
            "components": [{"id": "5", "name": "Common"}],
            "fixVersions": [{"id": "7", "name": "1.0.0"}],
            "versions": [{"id": "8", "name": "0.9.0"}],
            "created": "2024-01-01T00:00:00.000+0000",
            "updated": "2024-01-02T00:00:00.000+0000",
            "resolutiondate": "2024-01-03T00:00:00.000+0000",
            "duedate": "2024-01-31",
        },
    }

    result = normalize_jira_issue(issue, include_raw=False)
    dumped = result.record.model_dump()

    assert dumped["project"] == "Example Project"
    assert dumped["project_id"] == "10000"
    assert dumped["project_key"] == "ABC"
    assert dumped["issuetype"] == "Bug"
    assert dumped["issuetype_id"] == "1"
    assert dumped["summary"] == "Example"
    assert dumped["description"] == "Hello"
    assert dumped["status"] == "In Progress"
    assert dumped["status_id"] == "3"
    assert dumped["priority"] == "Major"
    assert dumped["resolution"] == "Fixed"
    assert dumped["assignee"] == "Alice"
    assert dumped["assignee_name"] == "alice"
    assert dumped["components"] == ["Common"]
    assert dumped["fixVersions"] == ["1.0.0"]
    assert dumped["versions"] == ["0.9.0"]
    assert dumped["created"].isoformat() == "2024-01-01T00:00:00+00:00"
    assert dumped["updated"].isoformat() == "2024-01-02T00:00:00+00:00"
    assert dumped["resolutiondate"].isoformat() == "2024-01-03T00:00:00+00:00"
    assert dumped["duedate"].isoformat() == "2024-01-31"

    assert "description_text" not in dumped
    assert "issue_type" not in dumped
    assert "fix_versions" not in dumped
    assert "affects_versions" not in dumped
    assert "created_at" not in dumped
    assert "updated_at" not in dumped
