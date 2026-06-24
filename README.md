# Extractory

Extractory is an unofficial, read-only Python toolkit for extracting, normalizing,
correlating, traversing, and exporting development workflow data from on-premise Jira
Data Center / Jira Server style REST APIs and Gerrit REST APIs.

It is not affiliated with Atlassian, Jira, Gerrit, or Google. Verify behavior against
your target instance and official documentation before using it in production.

## Install

```bash
uv add extractory
pip install extractory
```

## Jira Quickstart

```python
from extractory import BearerAuth, JiraClient, JiraConfig, normalize_jira_issue

config = JiraConfig(
    base_url="https://jira.company.local/jira",
    auth=BearerAuth(token="your-personal-access-token"),
)

with JiraClient(config) as client:
    issues = [
        normalize_jira_issue(issue.model_dump(by_alias=True)).record
        for issue in client.issues.search_all(
            'project = ABC ORDER BY updated DESC',
            fields=["summary", "status", "assignee", "updated"],
        )
    ]
```

Jira support targets `/rest/api/2` by default and preserves context paths such as
`https://jira.company.local/jira`. Jira Cloud-only search APIs such as
`/rest/api/3/search/jql` and `nextPageToken` are intentionally not used.

## Gerrit Quickstart

```python
from extractory import BasicAuth, GerritClient, GerritConfig, normalize_gerrit_change

config = GerritConfig(
    base_url="https://gerrit.company.local",
    auth=BasicAuth("user", "http-password"),
)

with GerritClient(config) as client:
    changes = [
        normalize_gerrit_change(change.model_dump(by_alias=True)).record
        for change in client.changes.query_all(
            "project:my/repo status:open",
            option_preset="standard",
        )
    ]
```

Authenticated Gerrit requests use the `/a/` path prefix by default. Gerrit XSSI JSON
prefixes are stripped before parsing.

## Selective Fetching

Extractory avoids over-fetching by default. Jira fields and expansions must be requested
explicitly:

```python
client.issues.search_all(
    "project = ABC",
    fields=["summary", "status", "updated"],
    exclude_fields=["comment", "worklog"],
)
```

Gerrit change options are repeated `o=` values:

```python
client.changes.query_all(
    "status:open project:my/repo",
    option_preset="minimal",
)
```

The `full` and `detailed` profiles are opt-in because they may request expensive fields,
messages, files, or changelog data.

## Callable Normalizers

```python
from typing import Any

from extractory.normalization import (
    FieldNormalizationContext,
    FieldNormalizationResult,
    FieldNormalizerRegistry,
)


def story_points(value: Any, context: FieldNormalizationContext) -> FieldNormalizationResult:
    return FieldNormalizationResult(
        columns={"story_points": None if value in (None, "") else float(value)},
        raw_value=value,
        normalized=True,
    )


registry = FieldNormalizerRegistry()
registry.register_field_id("customfield_10016", story_points)
```

Delimited text fields can be normalized to arrays by registering a configured splitter:

```python
from extractory.normalization import DelimitedTextArrayNormalizer, FieldNormalizerRegistry

registry = FieldNormalizerRegistry()
registry.register_field_id(
    "customfield_10030",
    DelimitedTextArrayNormalizer(delimiter=",", column="release_tags"),
)
```

Raw values are preserved when normalization fails unless you explicitly choose
`error_policy="raise"`.

Normalized records dump only fields that were observed or explicitly set during
normalization by default. A field that was not fetched is omitted from
`record.model_dump()`, while a fetched-but-empty field remains present with `None`,
`[]`, or `{}`. Pass `exclude_unset=False` to `model_dump()` if you need the full
record schema.

## Correlation and Graph Tools

```python
from extractory import correlate_issue_keys

links = correlate_issue_keys(gerrit_change_payload)
```

Traversal tools are explicitly bounded. Tune `max_depth`, `max_nodes`, `max_edges`, and
`max_api_calls` for your environment. Tools are read-only and return partial results with
warnings when limits are reached.

## CLI

The CLI is built with Typer and Rich.

```bash
extractory jira search \
  --base-url https://jira.company.local/jira \
  --pat "$EXTRACTORY_JIRA_PAT" \
  --jql "project = ABC ORDER BY updated DESC" \
  --fields summary,status,assignee,updated \
  --format jsonl

extractory gerrit query \
  --base-url https://gerrit.company.local \
  --query "project:my/repo status:merged" \
  --option-preset standard \
  --format jsonl

extractory tools jira graph ABC-123 --depth 2 --format json
extractory tools gerrit graph 12345 --depth 1 --format mermaid
```

The SDK does not read `.env` files or environment variables. CLI commands may read
`EXTRACTORY_*` variables for developer convenience, isolated to the CLI layer.

Never print or snapshot authorization headers, API tokens, passwords, cookies,
`JSESSIONID`, Seraph tokens, or client secrets.

## Development

```bash
uv sync --locked --all-extras --group docs
uv run --locked ruff format --check .
uv run --locked ruff check .
uv run --locked ty check
uv run --locked pytest -m "not live"
uv run --locked --group docs sphinx-build -W -b html docs docs/_build/html
uv build
```

Live tests are read-only and opt-in with `EXTRACTORY_ENABLE_LIVE_TESTS=true`.

Risk and release readiness summaries are deterministic helper heuristics. They are not
authoritative business decisions.
