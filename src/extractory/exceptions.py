"""Sanitized exception types for Extractory."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

SENSITIVE_KEYS = (
    "authorization",
    "api_token",
    "api-token",
    "pat",
    "password",
    "http_password",
    "cookie",
    "jsessionid",
    "seraph",
    "client_secret",
    "secret",
    "token",
)

_SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"(?i)(authorization\s*[:=]\s*)(bearer|basic)\s+[^\s,;]+"),
    re.compile(r"(?i)((?:api[_-]?token|pat|password|client[_-]?secret|token)\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"(?i)(JSESSIONID=)[^;\s]+"),
    re.compile(r"(?i)(seraph[^=]*=)[^;\s]+"),
)


def sanitize_text(value: object) -> str:
    """Return a string with common credential values redacted."""
    text = str(value)
    for pattern in _SENSITIVE_VALUE_PATTERNS:
        text = pattern.sub(r"\1<redacted>", text)
    return text


def sanitize_mapping(mapping: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return a shallow copy with sensitive keys redacted."""
    if mapping is None:
        return None
    sanitized: dict[str, Any] = {}
    for key, value in mapping.items():
        if any(sensitive in key.lower() for sensitive in SENSITIVE_KEYS):
            sanitized[key] = "<redacted>"
        elif isinstance(value, str):
            sanitized[key] = sanitize_text(value)
        else:
            sanitized[key] = value
    return sanitized


@dataclass(frozen=True)
class ErrorContext:
    """Metadata attached to an API error without exposing secrets."""

    source: str
    method: str | None = None
    endpoint: str | None = None
    status_code: int | None = None
    response_body: str | None = None
    retry_after: str | None = None


class ExtractoryError(Exception):
    """Base class for all Extractory exceptions."""


class AuthenticationError(ExtractoryError):
    """Raised when authentication fails."""


class PermissionDeniedError(ExtractoryError):
    """Raised when a resource is visible but not accessible."""


class NotFoundError(ExtractoryError):
    """Raised when a requested resource cannot be found."""


class RateLimitError(ExtractoryError):
    """Raised when an API responds with a rate-limit status."""

    def __init__(self, message: str, *, retry_after: str | None = None) -> None:
        super().__init__(sanitize_text(message))
        self.retry_after = retry_after


class ExtractoryAPIError(ExtractoryError):
    """Base class for sanitized upstream API errors."""

    def __init__(self, message: str, *, context: ErrorContext) -> None:
        super().__init__(sanitize_text(message))
        self.context = context
        self.status_code = context.status_code
        self.response_body = sanitize_text(context.response_body or "")
        self.retry_after = context.retry_after
        self.endpoint = sanitize_text(context.endpoint or "")


class JiraAPIError(ExtractoryAPIError):
    """Raised for Jira REST API failures."""


class GerritAPIError(ExtractoryAPIError):
    """Raised for Gerrit REST API failures."""


def map_status_error(source: str, context: ErrorContext) -> ExtractoryError:
    """Map a status code to a specific sanitized SDK exception."""
    status_code = context.status_code
    body = context.response_body or "API request failed"
    if status_code == 401:
        return AuthenticationError(sanitize_text(f"{source} authentication failed: {body}"))
    if status_code == 403:
        return PermissionDeniedError(sanitize_text(f"{source} permission denied: {body}"))
    if status_code == 404:
        return NotFoundError(sanitize_text(f"{source} resource not found: {body}"))
    if status_code == 429:
        return RateLimitError(
            sanitize_text(f"{source} rate limit exceeded: {body}"),
            retry_after=context.retry_after,
        )
    error_type = JiraAPIError if source == "jira" else GerritAPIError
    return error_type(
        sanitize_text(f"{source} API error {status_code}: {body}"),
        context=context,
    )
