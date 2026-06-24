import pytest

from extractory.normalization import FieldNormalizerRegistry, RegexExtractNormalizer
from extractory.normalization.gerrit import normalize_gerrit_change


def test_gerrit_issue_key_extraction_and_child_records() -> None:
    change = {
        "id": "repo~main~Iabc",
        "_number": 12,
        "project": "repo",
        "branch": "main",
        "change_id": "Iabc",
        "subject": "ABC-12 implement",
        "status": "NEW",
        "labels": {"Code-Review": {"value": 1}},
        "reviewers": {"REVIEWER": [{"_account_id": 1, "name": "Alice"}]},
        "revisions": {
            "abc": {
                "_number": 1,
                "commit": {"message": "ABC-12 details"},
                "files": {"src/a.py": {"lines_inserted": 2}},
            }
        },
    }

    result = normalize_gerrit_change(change)

    assert result.record.issue_keys == ["ABC-12"]
    assert any(child.__class__.__name__ == "GerritRevisionRecord" for child in result.child_records)
    assert any(child.__class__.__name__ == "GerritFileRecord" for child in result.child_records)


def test_gerrit_path_normalizer() -> None:
    registry = FieldNormalizerRegistry()
    registry.register_gerrit_path(
        ("change", "topic"),
        RegexExtractNormalizer(
            pattern=r"([A-Z]+-\d+)",
            numbered_group_output_keys={1: "topic_issue_key"},
        ),
    )
    change = {
        "id": "repo~main~Iabc",
        "_number": 12,
        "project": "repo",
        "branch": "main",
        "change_id": "Iabc",
        "subject": "topic",
        "topic": "ABC-12",
        "status": "NEW",
    }

    result = normalize_gerrit_change(change, normalizers=registry)

    assert result.record.model_extra is not None
    assert result.record.model_extra["topic_issue_key"] == "ABC-12"


def test_regex_extract_normalizer_can_use_named_groups() -> None:
    registry = FieldNormalizerRegistry()
    registry.register_gerrit_path(
        ("change", "topic"),
        RegexExtractNormalizer(
            pattern=r"(?P<issue_key>[A-Z]+-\d+)",
            named_group_output_keys={"issue_key": "topic_issue_key"},
        ),
    )
    change = {
        "id": "repo~main~Iabc",
        "_number": 12,
        "project": "repo",
        "branch": "main",
        "change_id": "Iabc",
        "subject": "topic",
        "topic": "ABC-12",
        "status": "NEW",
    }

    result = normalize_gerrit_change(change, normalizers=registry)

    assert result.record.model_extra is not None
    assert result.record.model_extra["topic_issue_key"] == "ABC-12"


def test_regex_extract_normalizer_requires_group_mapping() -> None:
    with pytest.raises(ValueError, match="at least one regex group mapping"):
        RegexExtractNormalizer(pattern=r"([A-Z]+-\d+)")


def test_model_dump_raw_wrapper_does_not_create_nested_raw() -> None:
    change = {
        "id": "repo~main~Iabc",
        "_number": 12,
        "project": "repo",
        "branch": "main",
        "change_id": "Iabc",
        "subject": "topic",
        "status": "NEW",
        "raw": {
            "id": "repo~main~Iabc",
            "_number": 12,
            "project": "repo",
            "branch": "main",
            "change_id": "Iabc",
            "subject": "topic",
            "status": "NEW",
        },
    }

    result = normalize_gerrit_change(change)

    assert result.record.raw is not None
    assert "raw" not in result.record.raw
