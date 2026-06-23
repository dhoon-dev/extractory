from datetime import UTC, datetime
from io import StringIO

from extractory.export import export_csv, export_jsonl


def test_jsonl_preserves_nested_values() -> None:
    handle = StringIO()

    export_jsonl([{"created": datetime(2026, 1, 1, tzinfo=UTC), "items": [1, 2]}], handle)

    assert '"items": [1, 2]' in handle.getvalue()
    assert "2026-01-01T00:00:00+00:00" in handle.getvalue()


def test_csv_json_encodes_lists_and_dicts() -> None:
    handle = StringIO()

    export_csv([{"key": "ABC-1", "items": [1, 2], "data": {"a": 1}}], handle)

    output = handle.getvalue()
    assert '"[1, 2]"' in output
    assert '"{""a"": 1}"' in output
