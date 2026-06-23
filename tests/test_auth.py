from extractory import BasicAuth, BearerAuth, NoAuth
from extractory.exceptions import sanitize_mapping, sanitize_text


def test_bearer_auth_header_is_created() -> None:
    assert BearerAuth("secret-token").auth_headers() == {"Authorization": "Bearer secret-token"}
    assert "secret-token" not in repr(BearerAuth("secret-token"))


def test_basic_auth_header_is_created_and_repr_is_redacted() -> None:
    auth = BasicAuth("alice", "secret-password")

    assert auth.auth_headers()["Authorization"].startswith("Basic ")
    assert "secret-password" not in repr(auth)


def test_no_auth_returns_no_headers() -> None:
    assert NoAuth().auth_headers() == {}


def test_sanitization_redacts_sensitive_values() -> None:
    text = sanitize_text("Authorization: Bearer abc JSESSIONID=secret")

    assert "abc" not in text
    assert "secret" not in text
    assert sanitize_mapping({"Authorization": "Bearer abc"}) == {"Authorization": "<redacted>"}
