"""Jira resource groups."""

from __future__ import annotations

import builtins
from collections.abc import AsyncIterator, Iterator, Sequence
from typing import Any, Literal
from urllib.parse import quote

from extractory._http import AsyncHttpRequester, HttpRequester, join_url_path
from extractory.config import JiraConfig
from extractory.jira.fields import JiraFieldCatalog
from extractory.jira.models import JiraIssue
from extractory.pagination import next_offset, should_continue_offset_page
from extractory.selection import serialize_csv, serialize_jira_fields


def _issue_model(payload: dict[str, Any], *, include_raw: bool = True) -> JiraIssue:
    if include_raw and "raw" not in payload:
        payload = {**payload, "raw": dict(payload)}
    return JiraIssue.model_validate(payload)


class JiraIssuesResource:
    """Sync Jira issue resource methods."""

    def __init__(self, requester: HttpRequester, config: JiraConfig) -> None:
        self._requester = requester
        self._config = config

    def _path(self, *parts: str) -> str:
        return join_url_path(self._config.api_base_path, *parts)

    def get(
        self,
        issue_key: str,
        *,
        fields: Sequence[str] | None = None,
        exclude_fields: Sequence[str] | None = None,
        expand: Sequence[str] | None = None,
        properties: Sequence[str] | None = None,
    ) -> JiraIssue:
        """Fetch one Jira issue by key or id."""
        params: dict[str, str] = {}
        serialized_fields = serialize_jira_fields(
            tuple(fields or ()),
            tuple(exclude_fields or ()),
        )
        if serialized_fields:
            params["fields"] = serialized_fields
        serialized_expand = serialize_csv(tuple(expand or ()))
        if serialized_expand:
            params["expand"] = serialized_expand
        serialized_properties = serialize_csv(tuple(properties or ()))
        if serialized_properties:
            params["properties"] = serialized_properties
        response = self._requester.request(
            "GET",
            self._path("issue", quote(issue_key, safe="")),
            params=params or None,
        )
        return _issue_model(response.json())

    def search(
        self,
        jql: str,
        *,
        fields: Sequence[str] | None = None,
        exclude_fields: Sequence[str] | None = None,
        expand: Sequence[str] | None = None,
        properties: Sequence[str] | None = None,
        start_at: int = 0,
        max_results: int | None = None,
        method: Literal["post", "get"] | None = None,
    ) -> dict[str, Any]:
        """Run one Jira JQL search page using POST or GET."""
        request_method = method or self._config.search_method
        page_size = max_results or self._config.page_size
        serialized_fields = serialize_jira_fields(
            tuple(fields or ()),
            tuple(exclude_fields or ()),
        )
        serialized_expand = serialize_csv(tuple(expand or ()))
        if request_method == "post":
            body: dict[str, Any] = {"jql": jql, "startAt": start_at, "maxResults": page_size}
            if serialized_fields:
                body["fields"] = serialized_fields.split(",")
            if serialized_expand:
                body["expand"] = serialized_expand
            if properties:
                body["properties"] = list(properties)
            response = self._requester.request("POST", self._path("search"), json=body)
        else:
            params: dict[str, Any] = {"jql": jql, "startAt": start_at, "maxResults": page_size}
            if serialized_fields:
                params["fields"] = serialized_fields
            if serialized_expand:
                params["expand"] = serialized_expand
            if properties:
                params["properties"] = serialize_csv(tuple(properties))
            response = self._requester.request("GET", self._path("search"), params=params)
        payload = response.json()
        if not isinstance(payload, dict):
            return {"issues": []}
        return payload

    def search_all(
        self,
        jql: str,
        *,
        fields: Sequence[str] | None = None,
        exclude_fields: Sequence[str] | None = None,
        expand: Sequence[str] | None = None,
        properties: Sequence[str] | None = None,
        page_size: int | None = None,
        method: Literal["post", "get"] | None = None,
    ) -> Iterator[JiraIssue]:
        """Yield all issues from an offset-paginated Jira search."""
        start_at = 0
        current_page_size = page_size or self._config.page_size
        while True:
            page = self.search(
                jql,
                fields=fields,
                exclude_fields=exclude_fields,
                expand=expand,
                properties=properties,
                start_at=start_at,
                max_results=current_page_size,
                method=method,
            )
            issues = page.get("issues") or []
            for issue in issues:
                yield _issue_model(issue)
            returned_count = len(issues)
            total = page.get("total")
            if not isinstance(total, int):
                total = None
            if not should_continue_offset_page(
                start_at=start_at,
                returned_count=returned_count,
                total=total,
            ):
                break
            next_start = next_offset(start_at, returned_count)
            if next_start <= start_at:
                break
            start_at = next_start

    def get_with_changelog(
        self, issue_key: str, *, fields: Sequence[str] | None = None
    ) -> JiraIssue:
        """Fetch an issue with changelog expansion."""
        return self.get(issue_key, fields=fields, expand=("changelog",))

    def get_comments(
        self,
        issue_key: str,
        *,
        start_at: int = 0,
        max_results: int | None = None,
    ) -> dict[str, Any]:
        """Fetch one Jira comments page."""
        response = self._requester.request(
            "GET",
            self._path("issue", quote(issue_key, safe=""), "comment"),
            params={"startAt": start_at, "maxResults": max_results or self._config.page_size},
        )
        payload = response.json()
        return payload if isinstance(payload, dict) else {"comments": []}

    def get_all_comments(
        self,
        issue_key: str,
        *,
        page_size: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Yield all comments for a Jira issue."""
        start_at = 0
        current_page_size = page_size or self._config.page_size
        while True:
            page = self.get_comments(issue_key, start_at=start_at, max_results=current_page_size)
            comments = page.get("comments") or []
            yield from comments
            returned_count = len(comments)
            total = page.get("total")
            if not isinstance(total, int):
                total = None
            if not should_continue_offset_page(
                start_at=start_at,
                returned_count=returned_count,
                total=total,
            ):
                break
            start_at = next_offset(start_at, returned_count)


class JiraFieldsResource:
    """Sync Jira field resource methods."""

    def __init__(self, requester: HttpRequester, config: JiraConfig) -> None:
        self._requester = requester
        self._config = config

    def list(self) -> JiraFieldCatalog:
        """Fetch the Jira field catalog."""
        response = self._requester.request(
            "GET", join_url_path(self._config.api_base_path, "field")
        )
        payload = response.json()
        return JiraFieldCatalog.from_payload(payload if isinstance(payload, list) else [])

    def find_by_name(self, name: str) -> builtins.list[object]:
        """Fetch fields and return entries with the requested display name."""
        return list(self.list().by_name(name))


class JiraProjectsResource:
    """Sync Jira project resource methods."""

    def __init__(self, requester: HttpRequester, config: JiraConfig) -> None:
        self._requester = requester
        self._config = config

    def list(self) -> builtins.list[dict[str, Any]]:
        """Fetch visible projects."""
        response = self._requester.request(
            "GET", join_url_path(self._config.api_base_path, "project")
        )
        payload = response.json()
        return payload if isinstance(payload, list) else []

    def get(self, project_key: str) -> dict[str, Any]:
        """Fetch one project by key or id."""
        response = self._requester.request(
            "GET",
            join_url_path(self._config.api_base_path, "project", quote(project_key, safe="")),
        )
        payload = response.json()
        return payload if isinstance(payload, dict) else {}


class JiraMyselfResource:
    """Sync Jira current-user resource methods."""

    def __init__(self, requester: HttpRequester, config: JiraConfig) -> None:
        self._requester = requester
        self._config = config

    def get(self) -> dict[str, Any]:
        """Fetch the current Jira user."""
        response = self._requester.request(
            "GET", join_url_path(self._config.api_base_path, "myself")
        )
        payload = response.json()
        return payload if isinstance(payload, dict) else {}


class AsyncJiraIssuesResource:
    """Async Jira issue resource methods."""

    def __init__(self, requester: AsyncHttpRequester, config: JiraConfig) -> None:
        self._requester = requester
        self._config = config

    def _path(self, *parts: str) -> str:
        return join_url_path(self._config.api_base_path, *parts)

    async def get(
        self,
        issue_key: str,
        *,
        fields: Sequence[str] | None = None,
        exclude_fields: Sequence[str] | None = None,
        expand: Sequence[str] | None = None,
        properties: Sequence[str] | None = None,
    ) -> JiraIssue:
        """Fetch one Jira issue by key or id."""
        params: dict[str, str] = {}
        serialized_fields = serialize_jira_fields(
            tuple(fields or ()),
            tuple(exclude_fields or ()),
        )
        if serialized_fields:
            params["fields"] = serialized_fields
        serialized_expand = serialize_csv(tuple(expand or ()))
        if serialized_expand:
            params["expand"] = serialized_expand
        serialized_properties = serialize_csv(tuple(properties or ()))
        if serialized_properties:
            params["properties"] = serialized_properties
        response = await self._requester.request(
            "GET",
            self._path("issue", quote(issue_key, safe="")),
            params=params or None,
        )
        return _issue_model(response.json())

    async def search(
        self,
        jql: str,
        *,
        fields: Sequence[str] | None = None,
        exclude_fields: Sequence[str] | None = None,
        expand: Sequence[str] | None = None,
        properties: Sequence[str] | None = None,
        start_at: int = 0,
        max_results: int | None = None,
        method: Literal["post", "get"] | None = None,
    ) -> dict[str, Any]:
        """Run one Jira JQL search page using POST or GET."""
        request_method = method or self._config.search_method
        page_size = max_results or self._config.page_size
        serialized_fields = serialize_jira_fields(
            tuple(fields or ()),
            tuple(exclude_fields or ()),
        )
        serialized_expand = serialize_csv(tuple(expand or ()))
        if request_method == "post":
            body: dict[str, Any] = {"jql": jql, "startAt": start_at, "maxResults": page_size}
            if serialized_fields:
                body["fields"] = serialized_fields.split(",")
            if serialized_expand:
                body["expand"] = serialized_expand
            if properties:
                body["properties"] = list(properties)
            response = await self._requester.request("POST", self._path("search"), json=body)
        else:
            params: dict[str, Any] = {"jql": jql, "startAt": start_at, "maxResults": page_size}
            if serialized_fields:
                params["fields"] = serialized_fields
            if serialized_expand:
                params["expand"] = serialized_expand
            if properties:
                params["properties"] = serialize_csv(tuple(properties))
            response = await self._requester.request("GET", self._path("search"), params=params)
        payload = response.json()
        return payload if isinstance(payload, dict) else {"issues": []}

    async def search_all(
        self,
        jql: str,
        *,
        fields: Sequence[str] | None = None,
        exclude_fields: Sequence[str] | None = None,
        expand: Sequence[str] | None = None,
        properties: Sequence[str] | None = None,
        page_size: int | None = None,
        method: Literal["post", "get"] | None = None,
    ) -> AsyncIterator[JiraIssue]:
        """Yield all issues from an offset-paginated Jira search."""
        start_at = 0
        current_page_size = page_size or self._config.page_size
        while True:
            page = await self.search(
                jql,
                fields=fields,
                exclude_fields=exclude_fields,
                expand=expand,
                properties=properties,
                start_at=start_at,
                max_results=current_page_size,
                method=method,
            )
            issues = page.get("issues") or []
            for issue in issues:
                yield _issue_model(issue)
            returned_count = len(issues)
            total = page.get("total")
            if not isinstance(total, int):
                total = None
            if not should_continue_offset_page(
                start_at=start_at,
                returned_count=returned_count,
                total=total,
            ):
                break
            next_start = next_offset(start_at, returned_count)
            if next_start <= start_at:
                break
            start_at = next_start


class AsyncJiraFieldsResource:
    """Async Jira field resource methods."""

    def __init__(self, requester: AsyncHttpRequester, config: JiraConfig) -> None:
        self._requester = requester
        self._config = config

    async def list(self) -> JiraFieldCatalog:
        """Fetch the Jira field catalog."""
        response = await self._requester.request(
            "GET",
            join_url_path(self._config.api_base_path, "field"),
        )
        payload = response.json()
        return JiraFieldCatalog.from_payload(payload if isinstance(payload, list) else [])

    async def find_by_name(self, name: str) -> builtins.list[object]:
        """Fetch fields and return entries with the requested display name."""
        return list((await self.list()).by_name(name))


class AsyncJiraProjectsResource:
    """Async Jira project resource methods."""

    def __init__(self, requester: AsyncHttpRequester, config: JiraConfig) -> None:
        self._requester = requester
        self._config = config

    async def list(self) -> builtins.list[dict[str, Any]]:
        """Fetch visible projects."""
        response = await self._requester.request(
            "GET",
            join_url_path(self._config.api_base_path, "project"),
        )
        payload = response.json()
        return payload if isinstance(payload, list) else []

    async def get(self, project_key: str) -> dict[str, Any]:
        """Fetch one project by key or id."""
        response = await self._requester.request(
            "GET",
            join_url_path(self._config.api_base_path, "project", quote(project_key, safe="")),
        )
        payload = response.json()
        return payload if isinstance(payload, dict) else {}


class AsyncJiraMyselfResource:
    """Async Jira current-user resource methods."""

    def __init__(self, requester: AsyncHttpRequester, config: JiraConfig) -> None:
        self._requester = requester
        self._config = config

    async def get(self) -> dict[str, Any]:
        """Fetch the current Jira user."""
        response = await self._requester.request(
            "GET",
            join_url_path(self._config.api_base_path, "myself"),
        )
        payload = response.json()
        return payload if isinstance(payload, dict) else {}
