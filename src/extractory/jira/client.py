"""Jira sync and async clients."""

from __future__ import annotations

from typing import Self

import httpx

from extractory._http import AsyncHttpRequester, HttpRequester
from extractory.config import JiraConfig
from extractory.jira.resources import (
    AsyncJiraFieldsResource,
    AsyncJiraIssuesResource,
    AsyncJiraMyselfResource,
    AsyncJiraProjectsResource,
    JiraFieldsResource,
    JiraIssuesResource,
    JiraMyselfResource,
    JiraProjectsResource,
)


class JiraClient:
    """Sync Jira Data Center/Server REST client."""

    def __init__(self, config: JiraConfig, *, client: httpx.Client | None = None) -> None:
        self.config = config
        headers = {"Accept": "application/json", **config.auth_provider.auth_headers()}
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=config.base_url,
            timeout=config.timeout,
            verify=config.verify_ssl,
            headers=headers,
        )
        self._requester = HttpRequester(self._client, source="jira", retry=config.retry)
        self.issues = JiraIssuesResource(self._requester, config)
        self.fields = JiraFieldsResource(self._requester, config)
        self.projects = JiraProjectsResource(self._requester, config)
        self.myself = JiraMyselfResource(self._requester, config)

    def __enter__(self) -> Self:
        """Enter a context manager."""
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        """Close owned resources when exiting a context manager."""
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP client if this client owns it."""
        if self._owns_client:
            self._client.close()


class AsyncJiraClient:
    """Async Jira Data Center/Server REST client."""

    def __init__(self, config: JiraConfig, *, client: httpx.AsyncClient | None = None) -> None:
        self.config = config
        headers = {"Accept": "application/json", **config.auth_provider.auth_headers()}
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=config.base_url,
            timeout=config.timeout,
            verify=config.verify_ssl,
            headers=headers,
        )
        self._requester = AsyncHttpRequester(self._client, source="jira", retry=config.retry)
        self.issues = AsyncJiraIssuesResource(self._requester, config)
        self.fields = AsyncJiraFieldsResource(self._requester, config)
        self.projects = AsyncJiraProjectsResource(self._requester, config)
        self.myself = AsyncJiraMyselfResource(self._requester, config)

    async def __aenter__(self) -> Self:
        """Enter an async context manager."""
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        """Close owned resources when exiting an async context manager."""
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying HTTP client if this client owns it."""
        if self._owns_client:
            await self._client.aclose()
