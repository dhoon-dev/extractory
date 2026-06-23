"""Gerrit sync and async clients."""

from __future__ import annotations

from typing import Self

import httpx

from extractory._http import AsyncHttpRequester, HttpRequester
from extractory.config import GerritConfig
from extractory.gerrit.resources import (
    AsyncGerritChangesResource,
    AsyncGerritConfigResource,
    GerritChangesResource,
    GerritConfigResource,
)


class GerritClient:
    """Sync Gerrit REST client."""

    def __init__(self, config: GerritConfig, *, client: httpx.Client | None = None) -> None:
        self.config = config
        headers = {
            "Accept": "application/json",
            **config.auth_provider.auth_headers(),
        }
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=config.base_url,
            timeout=config.timeout,
            verify=config.verify_ssl,
            headers=headers,
        )
        self._requester = HttpRequester(self._client, source="gerrit", retry=config.retry)
        self.changes = GerritChangesResource(self._requester, config)
        self.config_api = GerritConfigResource(self._requester, config)

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


class AsyncGerritClient:
    """Async Gerrit REST client."""

    def __init__(self, config: GerritConfig, *, client: httpx.AsyncClient | None = None) -> None:
        self.config = config
        headers = {
            "Accept": "application/json",
            **config.auth_provider.auth_headers(),
        }
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=config.base_url,
            timeout=config.timeout,
            verify=config.verify_ssl,
            headers=headers,
        )
        self._requester = AsyncHttpRequester(self._client, source="gerrit", retry=config.retry)
        self.changes = AsyncGerritChangesResource(self._requester, config)
        self.config_api = AsyncGerritConfigResource(self._requester, config)

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
