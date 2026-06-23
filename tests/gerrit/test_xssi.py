from extractory.gerrit import parse_gerrit_json_response


def test_parse_gerrit_json_response_strips_xssi_prefix() -> None:
    assert parse_gerrit_json_response(')]}\'\n{"ok": true}') == {"ok": True}


def test_parse_gerrit_json_response_handles_empty_body() -> None:
    assert parse_gerrit_json_response(")]}'\n") is None
