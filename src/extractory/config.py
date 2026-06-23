"""Configuration models for Jira and Gerrit clients."""

from __future__ import annotations

from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator

from extractory.auth import AuthProvider, NoAuth


def normalize_base_url(value: str) -> str:
    """Normalize a base URL while preserving context paths."""
    return value.rstrip("/")


class RetryConfig(BaseModel):
    """Conservative retry configuration for read-only API calls."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    enabled: bool = False
    max_attempts: int = Field(default=3, ge=1)
    backoff_factor: float = Field(default=0.5, ge=0)
    jitter: float = Field(default=0.1, ge=0)


class JiraConfig(BaseModel):
    """Configuration for on-prem Jira Data Center or Jira Server APIs."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    base_url: str
    api_version: str = "2"
    auth: Any | None = None
    search_method: Literal["post", "get"] = "post"
    timeout: float = 30.0
    page_size: int = Field(default=100, ge=1)
    verify_ssl: bool = True
    retry: RetryConfig = Field(default_factory=RetryConfig)

    @field_validator("base_url")
    @classmethod
    def _normalize_base_url(cls, value: str) -> str:
        return normalize_base_url(value)

    @property
    def auth_provider(self) -> AuthProvider:
        """Return the configured authentication provider."""
        return cast("AuthProvider", self.auth or NoAuth())

    @property
    def api_base_path(self) -> str:
        """Return the Jira REST API base path."""
        return f"/rest/api/{self.api_version}"


class GerritConfig(BaseModel):
    """Configuration for Gerrit REST APIs."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    base_url: str
    auth: Any | None = None
    use_authenticated_prefix: bool | None = None
    timeout: float = 30.0
    page_size: int = Field(default=100, ge=1)
    verify_ssl: bool = True
    retry: RetryConfig = Field(default_factory=RetryConfig)

    @field_validator("base_url")
    @classmethod
    def _normalize_base_url(cls, value: str) -> str:
        return normalize_base_url(value)

    @property
    def auth_provider(self) -> AuthProvider:
        """Return the configured authentication provider."""
        return cast("AuthProvider", self.auth or NoAuth())

    @property
    def authenticated_prefix_enabled(self) -> bool:
        """Return whether Gerrit `/a/` paths should be used."""
        if self.use_authenticated_prefix is not None:
            return self.use_authenticated_prefix
        return self.auth is not None
