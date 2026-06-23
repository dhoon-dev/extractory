---
name: extractory-commit-changes
description: Repository-specific workflow for creating Git commits in extractory. Use when the user asks Codex to commit changes, stage files, write a commit message, amend a commit, or verify commit-message compliance in this repo.
---

# Extractory Commit Changes

## Workflow

1. Inspect the tree and identify intended files:

```bash
git status --short --branch
git diff --name-status
```

2. Stage only files related to the user's request. Do not stage unrelated
   user changes.

3. Write a concise Conventional Commits message that follows this repo's rules:

- Allowed types: `feat`, `fix`, `chore`, `docs`, `test`, `refactor`, `ci`.
- Title format: `<type>: <summary>` or `<type>(scope): <summary>`.
- Title length: 50 characters or fewer.
- Body required after one blank line.
- Body lines: 72 characters or fewer.
- English only unless the user explicitly requests translation.

4. Let any local `commit-msg` hook run. Never bypass hooks with `--no-verify`.
   If a hook fails, fix the message and retry.

5. After commit, verify:

```bash
git status --short --branch
git show --stat --oneline --no-renames HEAD
```

6. Report the new commit hash and title.

## Message Examples

```text
ci: add GitHub Actions workflow

Mirror the existing GitLab quality gate in GitHub Actions so pushes and
pull requests run the same checks.
```

```text
fix: preserve Jira field names

Keep default Jira normalization keys close to their source field ids and
document the built-in field mapping table.
```
