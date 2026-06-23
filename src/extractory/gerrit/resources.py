"""Gerrit resource groups."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Sequence
from typing import Any
from urllib.parse import quote

from extractory._http import AsyncHttpRequester, HttpRequester, join_url_path
from extractory.config import GerritConfig
from extractory.gerrit.models import GerritChangeInfo, change_info, parse_gerrit_json_response
from extractory.selection import gerrit_options_params, normalize_gerrit_options


def _change_path(config: GerritConfig, *parts: str) -> str:
    prefix = "/a" if config.authenticated_prefix_enabled else ""
    return join_url_path(prefix, "changes", *parts)


def _revision_path(config: GerritConfig, change_id: str, revision: str, *parts: str) -> str:
    return _change_path(
        config,
        quote(change_id, safe=""),
        "revisions",
        quote(revision, safe=""),
        *parts,
    )


class GerritChangesResource:
    """Sync Gerrit change resource methods."""

    def __init__(self, requester: HttpRequester, config: GerritConfig) -> None:
        self._requester = requester
        self._config = config

    def _json(self, method: str, path: str, *, params: list[tuple[str, Any]] | None = None) -> Any:
        response = self._requester.request(method, path, params=params)
        return parse_gerrit_json_response(response.text)

    def query(
        self,
        query: str,
        *,
        limit: int | None = None,
        start: int | None = None,
        options: Sequence[object] | None = None,
        option_preset: str | None = None,
    ) -> list[GerritChangeInfo]:
        """Run one Gerrit change query page."""
        normalized = normalize_gerrit_options(tuple(options or ()), option_preset=option_preset)
        params: list[tuple[str, Any]] = [("q", query), ("n", limit or self._config.page_size)]
        if start is not None:
            params.append(("start", start))
        params.extend(gerrit_options_params(normalized))
        payload = self._json("GET", _change_path(self._config), params=params)
        changes = payload if isinstance(payload, list) else []
        return [change_info(change) for change in changes if isinstance(change, dict)]

    def query_all(
        self,
        query: str,
        *,
        page_size: int | None = None,
        options: Sequence[object] | None = None,
        option_preset: str | None = None,
    ) -> Iterator[GerritChangeInfo]:
        """Yield all Gerrit query results using `_more_changes` pagination."""
        start = 0
        current_page_size = page_size or self._config.page_size
        while True:
            page = self.query(
                query,
                limit=current_page_size,
                start=start,
                options=options,
                option_preset=option_preset,
            )
            yield from page
            if not page:
                break
            more = bool(page[-1].model_extra and page[-1].model_extra.get("_more_changes"))
            if not more:
                break
            next_start = start + len(page)
            if next_start <= start:
                break
            start = next_start

    def get(
        self,
        change_id: str,
        *,
        options: Sequence[object] | None = None,
        option_preset: str | None = None,
    ) -> GerritChangeInfo:
        """Fetch one Gerrit change."""
        normalized = normalize_gerrit_options(tuple(options or ()), option_preset=option_preset)
        payload = self._json(
            "GET",
            _change_path(self._config, quote(change_id, safe="")),
            params=gerrit_options_params(normalized),
        )
        return change_info(payload if isinstance(payload, dict) else {})

    def get_detail(
        self,
        change_id: str,
        *,
        options: Sequence[object] | None = None,
        option_preset: str | None = "standard",
    ) -> GerritChangeInfo:
        """Fetch one Gerrit change with a useful default detail preset."""
        return self.get(change_id, options=options, option_preset=option_preset)

    def get_comments(self, change_id: str) -> dict[str, Any]:
        """Fetch change comments."""
        payload = self._json(
            "GET", _change_path(self._config, quote(change_id, safe=""), "comments")
        )
        return payload if isinstance(payload, dict) else {}

    def get_files(self, change_id: str, *, revision: str = "current") -> dict[str, Any]:
        """Fetch files for a change revision."""
        payload = self._json("GET", _revision_path(self._config, change_id, revision, "files"))
        return payload if isinstance(payload, dict) else {}

    def get_related(self, change_id: str, *, revision: str = "current") -> dict[str, Any]:
        """Fetch related changes for a revision."""
        payload = self._json("GET", _revision_path(self._config, change_id, revision, "related"))
        return payload if isinstance(payload, dict) else {}

    def get_submitted_together(self, change_id: str) -> dict[str, Any]:
        """Fetch submitted-together changes."""
        payload = self._json(
            "GET",
            _change_path(self._config, quote(change_id, safe=""), "submitted_together"),
        )
        return payload if isinstance(payload, dict) else {}

    def get_included_in(self, change_id: str) -> dict[str, Any]:
        """Fetch branches and tags that include a change."""
        payload = self._json("GET", _change_path(self._config, quote(change_id, safe=""), "in"))
        return payload if isinstance(payload, dict) else {}


class GerritConfigResource:
    """Sync Gerrit config resource methods."""

    def __init__(self, requester: HttpRequester, config: GerritConfig) -> None:
        self._requester = requester
        self._config = config

    def get_version(self) -> str | None:
        """Fetch Gerrit server version."""
        prefix = "/a" if self._config.authenticated_prefix_enabled else ""
        response = self._requester.request(
            "GET", join_url_path(prefix, "config", "server", "version")
        )
        payload = parse_gerrit_json_response(response.text)
        return payload if isinstance(payload, str) else None


class AsyncGerritChangesResource:
    """Async Gerrit change resource methods."""

    def __init__(self, requester: AsyncHttpRequester, config: GerritConfig) -> None:
        self._requester = requester
        self._config = config

    async def _json(
        self,
        method: str,
        path: str,
        *,
        params: list[tuple[str, Any]] | None = None,
    ) -> Any:
        response = await self._requester.request(method, path, params=params)
        return parse_gerrit_json_response(response.text)

    async def query(
        self,
        query: str,
        *,
        limit: int | None = None,
        start: int | None = None,
        options: Sequence[object] | None = None,
        option_preset: str | None = None,
    ) -> list[GerritChangeInfo]:
        """Run one Gerrit change query page."""
        normalized = normalize_gerrit_options(tuple(options or ()), option_preset=option_preset)
        params: list[tuple[str, Any]] = [("q", query), ("n", limit or self._config.page_size)]
        if start is not None:
            params.append(("start", start))
        params.extend(gerrit_options_params(normalized))
        payload = await self._json("GET", _change_path(self._config), params=params)
        changes = payload if isinstance(payload, list) else []
        return [change_info(change) for change in changes if isinstance(change, dict)]

    async def query_all(
        self,
        query: str,
        *,
        page_size: int | None = None,
        options: Sequence[object] | None = None,
        option_preset: str | None = None,
    ) -> AsyncIterator[GerritChangeInfo]:
        """Yield all Gerrit query results using `_more_changes` pagination."""
        start = 0
        current_page_size = page_size or self._config.page_size
        while True:
            page = await self.query(
                query,
                limit=current_page_size,
                start=start,
                options=options,
                option_preset=option_preset,
            )
            for change in page:
                yield change
            if not page:
                break
            more = bool(page[-1].model_extra and page[-1].model_extra.get("_more_changes"))
            if not more:
                break
            next_start = start + len(page)
            if next_start <= start:
                break
            start = next_start

    async def get(
        self,
        change_id: str,
        *,
        options: Sequence[object] | None = None,
        option_preset: str | None = None,
    ) -> GerritChangeInfo:
        """Fetch one Gerrit change."""
        normalized = normalize_gerrit_options(tuple(options or ()), option_preset=option_preset)
        payload = await self._json(
            "GET",
            _change_path(self._config, quote(change_id, safe="")),
            params=gerrit_options_params(normalized),
        )
        return change_info(payload if isinstance(payload, dict) else {})


class AsyncGerritConfigResource:
    """Async Gerrit config resource methods."""

    def __init__(self, requester: AsyncHttpRequester, config: GerritConfig) -> None:
        self._requester = requester
        self._config = config

    async def get_version(self) -> str | None:
        """Fetch Gerrit server version."""
        prefix = "/a" if self._config.authenticated_prefix_enabled else ""
        response = await self._requester.request(
            "GET",
            join_url_path(prefix, "config", "server", "version"),
        )
        payload = parse_gerrit_json_response(response.text)
        return payload if isinstance(payload, str) else None
