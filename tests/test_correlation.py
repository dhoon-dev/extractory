from extractory import correlate_issue_keys, extract_issue_keys


def test_extract_issue_keys_deduplicates_in_order() -> None:
    assert extract_issue_keys("ABC-1 ABC-1 DEF-2") == ["ABC-1", "DEF-2"]


def test_correlate_issue_keys_from_gerrit_subject() -> None:
    records = correlate_issue_keys(
        {
            "id": "repo~main~Iabc",
            "_number": 123,
            "project": "repo",
            "branch": "main",
            "subject": "ABC-123 fix",
        }
    )

    assert records[0].issue_key == "ABC-123"
    assert records[0].confidence == "high"
