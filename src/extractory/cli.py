"""Typer and Rich command-line interface for Extractory."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Iterable
from typing import Annotated, Any, Literal

import typer
from rich.console import Console

from extractory._version import __version__
from extractory.auth import BasicAuth, BearerAuth, NoAuth
from extractory.config import GerritConfig, JiraConfig
from extractory.export import export_csv, export_jsonl, to_jsonable
from extractory.gerrit import GerritClient
from extractory.graph.export import graph_to_dot, graph_to_mermaid, graph_to_node_link_json
from extractory.jira import JiraClient
from extractory.normalization.gerrit import normalize_gerrit_change
from extractory.normalization.jira import normalize_jira_issue
from extractory.tools.cross_system import build_issue_change_graph, find_gerrit_changes_for_issue
from extractory.tools.gerrit_graph import GerritChangeGraphTool
from extractory.tools.jira_graph import JiraIssueGraphTool

console = Console()
err_console = Console(stderr=True)

app = typer.Typer(no_args_is_help=True, help="Extractory read-only Jira/Gerrit toolkit.")
jira_app = typer.Typer(no_args_is_help=True, help="Jira extraction commands.")
gerrit_app = typer.Typer(no_args_is_help=True, help="Gerrit extraction commands.")
tools_app = typer.Typer(no_args_is_help=True, help="Read-only analysis tools.")
tools_jira_app = typer.Typer(no_args_is_help=True, help="Jira graph and impact tools.")
tools_gerrit_app = typer.Typer(no_args_is_help=True, help="Gerrit graph and review tools.")
tools_cross_app = typer.Typer(no_args_is_help=True, help="Cross-system Jira/Gerrit tools.")

app.add_typer(jira_app, name="jira")
app.add_typer(gerrit_app, name="gerrit")
app.add_typer(tools_app, name="tools")
tools_app.add_typer(tools_jira_app, name="jira")
tools_app.add_typer(tools_gerrit_app, name="gerrit")
tools_app.add_typer(tools_cross_app, name="cross")

JsonFormat = Annotated[str, typer.Option("--format", help="Output format.")]
BaseUrl = Annotated[str | None, typer.Option("--base-url", help="Service base URL.")]
PageSize = Annotated[int, typer.Option("--page-size", min=1, help="Pagination page size.")]
VerifySsl = Annotated[
    bool, typer.Option("--verify-ssl/--no-verify-ssl", help="Verify TLS certificates.")
]
Depth = Annotated[int, typer.Option("--depth", min=0, help="Traversal depth.")]
MaxNodes = Annotated[int, typer.Option("--max-nodes", min=1, help="Maximum graph nodes.")]
MaxEdges = Annotated[int, typer.Option("--max-edges", min=1, help="Maximum graph edges.")]
MaxApiCalls = Annotated[int, typer.Option("--max-api-calls", min=1, help="Maximum API calls.")]


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"extractory {__version__}")
        raise typer.Exit


@app.callback()
def root(
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Show version."),
    ] = False,
) -> None:
    """Run Extractory commands."""
    del version


def _csv_arg(value: str | None) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip()) if value else ()


def _jira_auth(pat: str | None, username: str | None, password: str | None) -> object:
    token = pat or os.getenv("EXTRACTORY_JIRA_PAT")
    env_username = username or os.getenv("EXTRACTORY_JIRA_USERNAME")
    env_password = password or os.getenv("EXTRACTORY_JIRA_PASSWORD")
    if token:
        return BearerAuth(token)
    if env_username and env_password:
        return BasicAuth(env_username, env_password)
    return NoAuth()


def _gerrit_auth(token: str | None, username: str | None, password: str | None) -> object:
    bearer = token or os.getenv("EXTRACTORY_GERRIT_BEARER_TOKEN")
    env_username = username or os.getenv("EXTRACTORY_GERRIT_USERNAME")
    env_password = password or os.getenv("EXTRACTORY_GERRIT_HTTP_PASSWORD")
    if bearer:
        return BearerAuth(bearer)
    if env_username and env_password:
        return BasicAuth(env_username, env_password)
    return NoAuth()


def _jira_config(
    *,
    base_url: str | None,
    api_version: str,
    pat: str | None,
    username: str | None,
    password: str | None,
    method: str,
    page_size: int,
    verify_ssl: bool,
) -> JiraConfig:
    resolved_base_url = base_url or os.getenv("EXTRACTORY_JIRA_BASE_URL")
    if not resolved_base_url:
        err_console.print("[red]--base-url or EXTRACTORY_JIRA_BASE_URL is required[/red]")
        raise typer.Exit(2)
    return JiraConfig(
        base_url=resolved_base_url,
        api_version=api_version,
        auth=_jira_auth(pat, username, password),
        search_method=_search_method(method),
        page_size=page_size,
        verify_ssl=verify_ssl,
    )


def _search_method(method: str) -> Literal["post", "get"]:
    if method == "post":
        return "post"
    if method == "get":
        return "get"
    err_console.print("[red]--method must be either 'post' or 'get'[/red]")
    raise typer.Exit(2)


def _gerrit_config(
    *,
    base_url: str | None,
    bearer_token: str | None,
    username: str | None,
    http_password: str | None,
    page_size: int,
    verify_ssl: bool,
) -> GerritConfig:
    resolved_base_url = base_url or os.getenv("EXTRACTORY_GERRIT_BASE_URL")
    if not resolved_base_url:
        err_console.print("[red]--base-url or EXTRACTORY_GERRIT_BASE_URL is required[/red]")
        raise typer.Exit(2)
    return GerritConfig(
        base_url=resolved_base_url,
        auth=_gerrit_auth(bearer_token, username, http_password),
        page_size=page_size,
        verify_ssl=verify_ssl,
    )


def _write_output(data: Any, fmt: str) -> None:
    if fmt == "json":
        console.print_json(json=json.dumps(to_jsonable(data), ensure_ascii=False, sort_keys=True))
    elif fmt == "jsonl":
        export_jsonl(_ensure_iterable(data), sys.stdout)
    elif fmt == "csv":
        export_csv(_ensure_iterable(data), sys.stdout)
    elif fmt == "mermaid":
        console.print(graph_to_mermaid(data))
    elif fmt == "dot":
        console.print(graph_to_dot(data))
    elif fmt == "node-jsonl":
        export_jsonl(data.nodes, sys.stdout)
    elif fmt == "edge-jsonl":
        export_jsonl(data.edges, sys.stdout)
    elif fmt == "node-csv":
        export_csv(data.nodes, sys.stdout)
    elif fmt == "edge-csv":
        export_csv(data.edges, sys.stdout)
    else:
        console.print(graph_to_node_link_json(data))


def _ensure_iterable(data: Any) -> Iterable[Any]:
    if isinstance(data, list | tuple):
        return data
    return [data]


@jira_app.command("ping")
def jira_ping(
    base_url: BaseUrl = None,
    api_version: Annotated[str, typer.Option("--api-version", help="Jira REST API version.")] = "2",
    pat: Annotated[str | None, typer.Option("--pat", help="Jira personal access token.")] = None,
    username: Annotated[
        str | None, typer.Option("--username", help="Jira basic auth username.")
    ] = None,
    password: Annotated[
        str | None, typer.Option("--password", help="Jira basic auth password.")
    ] = None,
    method: Annotated[str, typer.Option("--method", help="Jira search method.")] = "post",
    page_size: PageSize = 100,
    verify_ssl: VerifySsl = True,
) -> None:
    """Fetch the current Jira user."""
    config = _jira_config(
        base_url=base_url,
        api_version=api_version,
        pat=pat,
        username=username,
        password=password,
        method=method,
        page_size=page_size,
        verify_ssl=verify_ssl,
    )
    with JiraClient(config) as client:
        _write_output(client.myself.get(), "json")


@jira_app.command("fields")
def jira_fields(
    base_url: BaseUrl = None,
    api_version: Annotated[str, typer.Option("--api-version")] = "2",
    pat: Annotated[str | None, typer.Option("--pat")] = None,
    username: Annotated[str | None, typer.Option("--username")] = None,
    password: Annotated[str | None, typer.Option("--password")] = None,
    method: Annotated[str, typer.Option("--method")] = "post",
    page_size: PageSize = 100,
    verify_ssl: VerifySsl = True,
) -> None:
    """Fetch Jira field catalog entries."""
    config = _jira_config(
        base_url=base_url,
        api_version=api_version,
        pat=pat,
        username=username,
        password=password,
        method=method,
        page_size=page_size,
        verify_ssl=verify_ssl,
    )
    with JiraClient(config) as client:
        _write_output(client.fields.list().fields, "json")


@jira_app.command("search")
def jira_search(
    jql: Annotated[str, typer.Option("--jql", help="Jira JQL query.")],
    base_url: BaseUrl = None,
    api_version: Annotated[str, typer.Option("--api-version")] = "2",
    pat: Annotated[str | None, typer.Option("--pat")] = None,
    username: Annotated[str | None, typer.Option("--username")] = None,
    password: Annotated[str | None, typer.Option("--password")] = None,
    method: Annotated[str, typer.Option("--method")] = "post",
    page_size: PageSize = 100,
    verify_ssl: VerifySsl = True,
    fields: Annotated[str | None, typer.Option("--fields")] = None,
    exclude_fields: Annotated[str | None, typer.Option("--exclude-fields")] = None,
    expand: Annotated[str | None, typer.Option("--expand")] = None,
    fmt: JsonFormat = "jsonl",
) -> None:
    """Search Jira issues and output normalized records."""
    config = _jira_config(
        base_url=base_url,
        api_version=api_version,
        pat=pat,
        username=username,
        password=password,
        method=method,
        page_size=page_size,
        verify_ssl=verify_ssl,
    )
    with JiraClient(config) as client:
        issues = [
            normalize_jira_issue(issue.model_dump(by_alias=True)).record
            for issue in client.issues.search_all(
                jql,
                fields=_csv_arg(fields),
                exclude_fields=_csv_arg(exclude_fields),
                expand=_csv_arg(expand),
            )
        ]
        _write_output(issues, fmt)


@jira_app.command("issue")
def jira_issue(
    issue_key: Annotated[str, typer.Argument(help="Issue key or id.")],
    base_url: BaseUrl = None,
    api_version: Annotated[str, typer.Option("--api-version")] = "2",
    pat: Annotated[str | None, typer.Option("--pat")] = None,
    username: Annotated[str | None, typer.Option("--username")] = None,
    password: Annotated[str | None, typer.Option("--password")] = None,
    method: Annotated[str, typer.Option("--method")] = "post",
    page_size: PageSize = 100,
    verify_ssl: VerifySsl = True,
    fields: Annotated[str | None, typer.Option("--fields")] = None,
    expand: Annotated[str | None, typer.Option("--expand")] = None,
    fmt: JsonFormat = "json",
) -> None:
    """Fetch one Jira issue and output a normalized record."""
    config = _jira_config(
        base_url=base_url,
        api_version=api_version,
        pat=pat,
        username=username,
        password=password,
        method=method,
        page_size=page_size,
        verify_ssl=verify_ssl,
    )
    with JiraClient(config) as client:
        issue = client.issues.get(issue_key, fields=_csv_arg(fields), expand=_csv_arg(expand))
        _write_output(normalize_jira_issue(issue.model_dump(by_alias=True)).record, fmt)


@jira_app.command("comments")
def jira_comments(
    issue_key: Annotated[str, typer.Argument(help="Issue key or id.")],
    base_url: BaseUrl = None,
    api_version: Annotated[str, typer.Option("--api-version")] = "2",
    pat: Annotated[str | None, typer.Option("--pat")] = None,
    username: Annotated[str | None, typer.Option("--username")] = None,
    password: Annotated[str | None, typer.Option("--password")] = None,
    method: Annotated[str, typer.Option("--method")] = "post",
    page_size: PageSize = 100,
    verify_ssl: VerifySsl = True,
    fmt: JsonFormat = "jsonl",
) -> None:
    """Fetch Jira issue comments."""
    config = _jira_config(
        base_url=base_url,
        api_version=api_version,
        pat=pat,
        username=username,
        password=password,
        method=method,
        page_size=page_size,
        verify_ssl=verify_ssl,
    )
    with JiraClient(config) as client:
        _write_output(list(client.issues.get_all_comments(issue_key)), fmt)


@jira_app.command("changelog")
def jira_changelog(
    issue_key: Annotated[str, typer.Argument(help="Issue key or id.")],
    base_url: BaseUrl = None,
    api_version: Annotated[str, typer.Option("--api-version")] = "2",
    pat: Annotated[str | None, typer.Option("--pat")] = None,
    username: Annotated[str | None, typer.Option("--username")] = None,
    password: Annotated[str | None, typer.Option("--password")] = None,
    method: Annotated[str, typer.Option("--method")] = "post",
    page_size: PageSize = 100,
    verify_ssl: VerifySsl = True,
    fmt: JsonFormat = "json",
) -> None:
    """Fetch a Jira issue with changelog expansion."""
    config = _jira_config(
        base_url=base_url,
        api_version=api_version,
        pat=pat,
        username=username,
        password=password,
        method=method,
        page_size=page_size,
        verify_ssl=verify_ssl,
    )
    with JiraClient(config) as client:
        _write_output(client.issues.get_with_changelog(issue_key).raw, fmt)


@gerrit_app.command("ping")
def gerrit_ping(
    base_url: BaseUrl = None,
    username: Annotated[str | None, typer.Option("--username")] = None,
    http_password: Annotated[str | None, typer.Option("--http-password")] = None,
    bearer_token: Annotated[str | None, typer.Option("--bearer-token")] = None,
    page_size: PageSize = 100,
    verify_ssl: VerifySsl = True,
) -> None:
    """Fetch Gerrit server version."""
    config = _gerrit_config(
        base_url=base_url,
        bearer_token=bearer_token,
        username=username,
        http_password=http_password,
        page_size=page_size,
        verify_ssl=verify_ssl,
    )
    with GerritClient(config) as client:
        _write_output({"version": client.config_api.get_version()}, "json")


@gerrit_app.command("query")
def gerrit_query(
    query: Annotated[str, typer.Option("--query", help="Gerrit query.")],
    base_url: BaseUrl = None,
    username: Annotated[str | None, typer.Option("--username")] = None,
    http_password: Annotated[str | None, typer.Option("--http-password")] = None,
    bearer_token: Annotated[str | None, typer.Option("--bearer-token")] = None,
    page_size: PageSize = 100,
    verify_ssl: VerifySsl = True,
    option: Annotated[
        list[str] | None, typer.Option("--option", help="Repeated Gerrit o= option.")
    ] = None,
    options: Annotated[
        str | None, typer.Option("--options", help="Comma-separated Gerrit options.")
    ] = None,
    option_preset: Annotated[str | None, typer.Option("--option-preset")] = "standard",
    fmt: JsonFormat = "jsonl",
) -> None:
    """Query Gerrit changes and output normalized records."""
    config = _gerrit_config(
        base_url=base_url,
        bearer_token=bearer_token,
        username=username,
        http_password=http_password,
        page_size=page_size,
        verify_ssl=verify_ssl,
    )
    selected_options = list(option or []) + list(_csv_arg(options))
    with GerritClient(config) as client:
        changes = [
            normalize_gerrit_change(change.model_dump(by_alias=True)).record
            for change in client.changes.query_all(
                query,
                options=selected_options,
                option_preset=option_preset,
            )
        ]
        _write_output(changes, fmt)


@gerrit_app.command("change")
def gerrit_change(
    change_id: Annotated[str, typer.Argument(help="Change id or number.")],
    base_url: BaseUrl = None,
    username: Annotated[str | None, typer.Option("--username")] = None,
    http_password: Annotated[str | None, typer.Option("--http-password")] = None,
    bearer_token: Annotated[str | None, typer.Option("--bearer-token")] = None,
    page_size: PageSize = 100,
    verify_ssl: VerifySsl = True,
    option_preset: Annotated[str | None, typer.Option("--option-preset")] = "standard",
    fmt: JsonFormat = "json",
) -> None:
    """Fetch one Gerrit change."""
    config = _gerrit_config(
        base_url=base_url,
        bearer_token=bearer_token,
        username=username,
        http_password=http_password,
        page_size=page_size,
        verify_ssl=verify_ssl,
    )
    with GerritClient(config) as client:
        change = client.changes.get(change_id, option_preset=option_preset)
        _write_output(normalize_gerrit_change(change.model_dump(by_alias=True)).record, fmt)


@tools_jira_app.command("graph")
def tools_jira_graph(
    issue_key: Annotated[list[str], typer.Argument(help="Root issue key(s).")],
    base_url: BaseUrl = None,
    api_version: Annotated[str, typer.Option("--api-version")] = "2",
    pat: Annotated[str | None, typer.Option("--pat")] = None,
    username: Annotated[str | None, typer.Option("--username")] = None,
    password: Annotated[str | None, typer.Option("--password")] = None,
    method: Annotated[str, typer.Option("--method")] = "post",
    page_size: PageSize = 100,
    verify_ssl: VerifySsl = True,
    depth: Depth = 1,
    max_nodes: MaxNodes = 500,
    max_edges: MaxEdges = 2000,
    max_api_calls: MaxApiCalls = 1000,
    fmt: JsonFormat = "json",
) -> None:
    """Crawl a bounded Jira issue graph."""
    del max_api_calls
    config = _jira_config(
        base_url=base_url,
        api_version=api_version,
        pat=pat,
        username=username,
        password=password,
        method=method,
        page_size=page_size,
        verify_ssl=verify_ssl,
    )
    with JiraClient(config) as client:
        graph = JiraIssueGraphTool(client).crawl_connected_issues(
            issue_key,
            max_depth=depth,
            max_nodes=max_nodes,
            max_edges=max_edges,
        )
        _write_output(graph, fmt)


@tools_gerrit_app.command("graph")
def tools_gerrit_graph(
    change_id: Annotated[list[str], typer.Argument(help="Root change id(s).")],
    base_url: BaseUrl = None,
    username: Annotated[str | None, typer.Option("--username")] = None,
    http_password: Annotated[str | None, typer.Option("--http-password")] = None,
    bearer_token: Annotated[str | None, typer.Option("--bearer-token")] = None,
    page_size: PageSize = 100,
    verify_ssl: VerifySsl = True,
    depth: Depth = 1,
    max_nodes: MaxNodes = 500,
    max_edges: MaxEdges = 2000,
    max_api_calls: MaxApiCalls = 1000,
    fmt: JsonFormat = "json",
) -> None:
    """Crawl a bounded Gerrit related-change graph."""
    del max_api_calls
    config = _gerrit_config(
        base_url=base_url,
        bearer_token=bearer_token,
        username=username,
        http_password=http_password,
        page_size=page_size,
        verify_ssl=verify_ssl,
    )
    with GerritClient(config) as client:
        graph = GerritChangeGraphTool(client).crawl_related_changes(
            change_id,
            max_depth=depth,
            max_nodes=max_nodes,
            max_edges=max_edges,
        )
        _write_output(graph, fmt)


@tools_cross_app.command("issue-changes")
def tools_cross_issue_changes(
    issue_key: Annotated[str, typer.Argument(help="Jira issue key.")],
    base_url: BaseUrl = None,
    username: Annotated[str | None, typer.Option("--username")] = None,
    http_password: Annotated[str | None, typer.Option("--http-password")] = None,
    bearer_token: Annotated[str | None, typer.Option("--bearer-token")] = None,
    page_size: PageSize = 100,
    verify_ssl: VerifySsl = True,
    gerrit_query_base: Annotated[str | None, typer.Option("--gerrit-query-base")] = None,
    fmt: JsonFormat = "jsonl",
) -> None:
    """Find Gerrit changes that mention a Jira issue."""
    config = _gerrit_config(
        base_url=base_url,
        bearer_token=bearer_token,
        username=username,
        http_password=http_password,
        page_size=page_size,
        verify_ssl=verify_ssl,
    )
    with GerritClient(config) as client:
        _write_output(
            find_gerrit_changes_for_issue(client, issue_key, query_base=gerrit_query_base),
            fmt,
        )


@tools_cross_app.command("graph")
def tools_cross_graph(
    issue_key: Annotated[list[str], typer.Argument(help="Root Jira issue key(s).")],
    jira_base_url: Annotated[str | None, typer.Option("--jira-base-url")] = None,
    gerrit_base_url: Annotated[str | None, typer.Option("--gerrit-base-url")] = None,
    jira_pat: Annotated[str | None, typer.Option("--jira-pat")] = None,
    gerrit_bearer_token: Annotated[str | None, typer.Option("--gerrit-bearer-token")] = None,
    page_size: PageSize = 100,
    verify_ssl: VerifySsl = True,
    jira_depth: Annotated[int, typer.Option("--jira-depth", min=0)] = 1,
    gerrit_depth: Annotated[int, typer.Option("--gerrit-depth", min=0)] = 1,
    fmt: JsonFormat = "json",
) -> None:
    """Build a bounded graph connecting Jira issues and Gerrit changes."""
    jira_config = JiraConfig(
        base_url=jira_base_url or os.getenv("EXTRACTORY_JIRA_BASE_URL") or "",
        auth=BearerAuth(jira_pat) if jira_pat else NoAuth(),
        page_size=page_size,
        verify_ssl=verify_ssl,
    )
    gerrit_config = GerritConfig(
        base_url=gerrit_base_url or os.getenv("EXTRACTORY_GERRIT_BASE_URL") or "",
        auth=BearerAuth(gerrit_bearer_token) if gerrit_bearer_token else NoAuth(),
        page_size=page_size,
        verify_ssl=verify_ssl,
    )
    with JiraClient(jira_config) as jira_client, GerritClient(gerrit_config) as gerrit_client:
        graph = build_issue_change_graph(
            jira_client,
            gerrit_client,
            issue_key,
            jira_depth=jira_depth,
            gerrit_depth=gerrit_depth,
        )
        _write_output(graph, fmt)


def main() -> None:
    """Run the Typer CLI app."""
    app()


if __name__ == "__main__":
    main()
