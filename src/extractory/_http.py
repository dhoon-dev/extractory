"""Shared HTTP helpers for Extractory clients."""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Mapping
from typing import Any

import httpx

from extractory.config import RetryConfig
from extractory.exceptions import ErrorContext, ExtractoryError, map_status_error, sanitize_text

JsonObject = dict[str, Any]

_RETRY_STATUSES = {429, 500, 502, 503, 504}


def join_url_path(base_path: str, *parts: str) -> str:
    """Join URL path segments without losing Jira context-path compatibility."""
    cleaned = [base_path.strip("/")]
    cleaned.extend(part.strip("/") for part in parts if part)
    return "/" + "/".join(part for part in cleaned if part)


def response_error(source: str, method: str, url: str, response: httpx.Response) -> ExtractoryError:
    """Return a sanitized exception for a non-successful response."""
    context = ErrorContext(
        source=source,
        method=method,
        endpoint=url,
        status_code=response.status_code,
        response_body=sanitize_text(response.text),
        retry_after=response.headers.get("Retry-After"),
    )
    return map_status_error(source, context)


def should_retry(
    response: httpx.Response | None, exc: Exception | None, retry: RetryConfig
) -> bool:
    """Return whether a request should be retried."""
    if not retry.enabled:
        return False
    if exc is not None:
        return isinstance(exc, (httpx.TimeoutException, httpx.TransportError))
    return response is not None and response.status_code in _RETRY_STATUSES


def retry_delay(attempt: int, response: httpx.Response | None, retry: RetryConfig) -> float:
    """Compute a retry delay, respecting Retry-After when present."""
    if response is not None:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return max(float(retry_after), 0.0)
            except ValueError:
                return retry.backoff_factor
    base = retry.backoff_factor * (2 ** max(attempt - 1, 0))
    return base + random.uniform(0, retry.jitter)  # noqa: S311


class HttpRequester:
    """Small sync HTTP wrapper with conservative optional retries."""

    def __init__(self, client: httpx.Client, *, source: str, retry: RetryConfig) -> None:
        self._client = client
        self._source = source
        self._retry = retry

    def request(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | list[tuple[str, Any]] | None = None,
        json: JsonObject | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        """Issue a request and raise sanitized SDK exceptions on failure."""
        last_exc: Exception | None = None
        response: httpx.Response | None = None
        for attempt in range(1, self._retry.max_attempts + 1):
            try:
                response = self._client.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    headers=headers,
                )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_exc = exc
                if attempt == self._retry.max_attempts or not should_retry(None, exc, self._retry):
                    raise ExtractoryError(sanitize_text(exc)) from exc
            else:
                if response.status_code < 400:
                    return response
                if attempt == self._retry.max_attempts or not should_retry(
                    response, None, self._retry
                ):
                    raise response_error(self._source, method, url, response)
            time.sleep(retry_delay(attempt, response, self._retry))
        if last_exc is not None:
            raise ExtractoryError(sanitize_text(last_exc)) from last_exc
        if response is not None:
            raise response_error(self._source, method, url, response)
        raise ExtractoryError("Request failed before receiving a response")


class AsyncHttpRequester:
    """Small async HTTP wrapper with conservative optional retries."""

    def __init__(self, client: httpx.AsyncClient, *, source: str, retry: RetryConfig) -> None:
        self._client = client
        self._source = source
        self._retry = retry

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | list[tuple[str, Any]] | None = None,
        json: JsonObject | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        """Issue a request and raise sanitized SDK exceptions on failure."""
        last_exc: Exception | None = None
        response: httpx.Response | None = None
        for attempt in range(1, self._retry.max_attempts + 1):
            try:
                response = await self._client.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    headers=headers,
                )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_exc = exc
                if attempt == self._retry.max_attempts or not should_retry(None, exc, self._retry):
                    raise ExtractoryError(sanitize_text(exc)) from exc
            else:
                if response.status_code < 400:
                    return response
                if attempt == self._retry.max_attempts or not should_retry(
                    response, None, self._retry
                ):
                    raise response_error(self._source, method, url, response)
            await asyncio.sleep(retry_delay(attempt, response, self._retry))
        if last_exc is not None:
            raise ExtractoryError(sanitize_text(last_exc)) from last_exc
        if response is not None:
            raise response_error(self._source, method, url, response)
        raise ExtractoryError("Request failed before receiving a response")
