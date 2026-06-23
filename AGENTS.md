# AGENTS.md

## Project Scope

Extractory is an unofficial, read-only Python SDK and analytics toolkit for on-premise
Jira Data Center / Jira Server style REST APIs and Gerrit REST APIs. Keep public APIs
explicit, typed, and conservative. Generated source, documentation, comments, tests, and
commit-facing text must be written in English unless a translation is explicitly requested.

## Sources of Truth

- Official Jira Data Center REST API documentation for the target instance version.
- Official Gerrit REST API documentation for the target Gerrit version.
- Target company Jira/Gerrit behavior observed through mocked or opt-in read-only live tests.
- Repo-local code, tests, lockfiles, and CI configuration.

Do not implement Jira Cloud v3-only behavior unless explicitly requested. Do not use
`/rest/api/3/search/jql` or `nextPageToken` for the current Jira target. Prefer configurable
behavior over hard-coded Jira version assumptions.

## Dependency and Tooling Rules

- Python targets 3.12+.
- Use `uv` for project commands.
- Keep runtime dependencies minimal: `httpx` and `pydantic`.
- Before changing behavior that depends on third-party packages or external tools, consult
current documentation first. If Context7 is unavailable, inspect local installed packages or
official docs.

## Quality Gate

Run focused checks first. Before broad handoff, run:

```bash
uv sync --locked --all-extras --group docs
uv run --locked ruff format --check .
uv run --locked ruff check .
uv run --locked ty check
uv run --locked pytest -m "not live"
uv run --locked --group docs sphinx-build -W -b html docs docs/_build/html
uv build
```

## Credentials and Live Tests

- SDK code must not read environment variables or `.env` files.
- CLI code may read documented `EXTRACTORY_*` variables.
- Never commit `.env` or real credentials.
- Never expose Authorization headers, API tokens, PATs, Gerrit HTTP passwords, passwords,
  cookies, `JSESSIONID`, Seraph tokens, or client secrets in exceptions, logs, docs examples,
  or test snapshots.
- Live tests must be read-only and require `EXTRACTORY_ENABLE_LIVE_TESTS=true`.

## CI

Use both `.gitlab-ci.yml` and `.github/workflows/ci.yml`. CI should run the same quality
gate and archive `dist/` and Sphinx HTML artifacts. Do not add release publishing without
a repository policy.

## Implementation Guidelines

- Keep sync and async clients behaviorally aligned.
- Preserve raw payloads when requested.
- Keep graph/traversal tools bounded by depth, node, edge, and API-call limits.
- Do not add database persistence, web servers, MCP servers, pandas, SQLAlchemy, networkx,
  or graphviz in v0 unless explicitly requested. Typer and Rich are intentionally used for
  the CLI because the user explicitly requested them.
- Prefer callable normalizers over declarative DSLs in v0.

## Documentation

Keep public classes, functions, resources, exceptions, and Pydantic models documented with
useful docstrings. Document read-only behavior and traversal cost warnings.

## Commit Messages

Use the repo-local `$extractory-commit-changes` skill when commits are requested. Commit
messages must use concise Conventional Commit style.
