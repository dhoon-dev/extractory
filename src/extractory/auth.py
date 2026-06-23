"""Authentication helpers for Jira and Gerrit clients."""

from __future__ import annotations

import base64
from typing import Protocol


class AuthProvider(Protocol):
    """Protocol implemented by Extractory authentication helpers."""

    def auth_headers(self) -> dict[str, str]:
        """Return HTTP headers for a request."""


class NoAuth:
    """Anonymous read-only access."""

    def auth_headers(self) -> dict[str, str]:
        """Return no authentication headers."""
        return {}


class BearerAuth:
    """Bearer token authentication, usually Jira PAT or Gerrit token."""

    def __init__(self, token: str) -> None:
        self._token = token

    def auth_headers(self) -> dict[str, str]:
        """Return an Authorization header."""
        return {"Authorization": f"Bearer {self._token}"}

    def __repr__(self) -> str:
        """Return a redacted representation."""
        return "BearerAuth(token=<redacted>)"


class BasicAuth:
    """HTTP Basic authentication."""

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self._password = password

    def auth_headers(self) -> dict[str, str]:
        """Return an Authorization header."""
        token = base64.b64encode(f"{self.username}:{self._password}".encode()).decode()
        return {"Authorization": f"Basic {token}"}

    def __repr__(self) -> str:
        """Return a redacted representation."""
        return f"BasicAuth(username={self.username!r}, password=<redacted>)"
