from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ALLOWED_TYPES = ("feat", "fix", "chore", "docs", "test", "refactor", "ci")
MAX_TITLE_LENGTH = 50
MAX_BODY_LINE_LENGTH = 72
FIELD_SEPARATOR = "\x1f"
RECORD_SEPARATOR = "\x1e"
ZERO_SHA = "0" * 40

TITLE_PATTERN = re.compile(rf"^({'|'.join(ALLOWED_TYPES)})(?:\([a-z0-9][a-z0-9._-]*\))?!?: .+$")


@dataclass(frozen=True)
class CommitMessage:
    label: str
    message: str


@dataclass(frozen=True)
class ValidationFailure:
    label: str
    errors: list[str]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate project commit message rules.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--message-file", type=Path, help="Validate one commit message file.")
    source.add_argument(
        "--range",
        dest="rev_range",
        help="Validate commits in a git revision range.",
    )
    source.add_argument(
        "--github-event",
        action="store_true",
        help="Validate commits for the current GitHub Actions event.",
    )
    args = parser.parse_args()

    try:
        messages = _load_messages(args)
    except (OSError, RuntimeError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"Unable to read commit messages: {exc}", file=sys.stderr)
        return 1

    failures = [
        ValidationFailure(message.label, errors)
        for message in messages
        if (errors := _validate_message(message.message))
    ]
    if failures:
        _print_failures(failures)
        return 1

    if messages:
        print(f"Validated {len(messages)} commit message(s).")
    else:
        print("No commit messages found to validate.")
    return 0


def _load_messages(args: argparse.Namespace) -> list[CommitMessage]:
    if args.message_file is not None:
        message = _read_message_file(args.message_file)
        return [CommitMessage(str(args.message_file), message)]
    if args.rev_range is not None:
        return _messages_from_git_log([args.rev_range])
    return _messages_from_github_event()


def _read_message_file(path: Path) -> str:
    raw_message = path.read_text(encoding="utf-8")
    return _strip_git_comments(raw_message)


def _strip_git_comments(raw_message: str) -> str:
    lines: list[str] = []
    for line in raw_message.splitlines():
        if line.startswith("#"):
            continue
        lines.append(line.rstrip())
    return "\n".join(lines).strip("\n")


def _messages_from_github_event() -> list[CommitMessage]:
    event_name = os.environ.get("GITHUB_EVENT_NAME")
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_name or not event_path:
        msg = "GITHUB_EVENT_NAME and GITHUB_EVENT_PATH must be set."
        raise RuntimeError(msg)

    event = _read_json(Path(event_path))
    if event_name == "push":
        return _messages_from_push_event(event)
    if event_name == "pull_request":
        return _messages_from_pull_request_event(event)
    if event_name == "workflow_dispatch":
        return _messages_from_git_log(["-1", "HEAD"])

    return []


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        msg = f"Expected JSON object in {path}."
        raise ValueError(msg)
    return data


def _messages_from_push_event(event: dict[str, Any]) -> list[CommitMessage]:
    commits = event.get("commits", [])
    if isinstance(commits, list) and commits:
        messages: list[CommitMessage] = []
        for commit in commits:
            if not isinstance(commit, dict):
                continue
            message = commit.get("message")
            sha = commit.get("id")
            if isinstance(message, str) and isinstance(sha, str):
                messages.append(CommitMessage(sha, message))
        return messages

    after = event.get("after")
    if isinstance(after, str) and after and after != ZERO_SHA:
        return _messages_from_git_log(["-1", after])
    return []


def _messages_from_pull_request_event(event: dict[str, Any]) -> list[CommitMessage]:
    pull_request = event.get("pull_request")
    if not isinstance(pull_request, dict):
        msg = "Missing pull_request object in GitHub event payload."
        raise ValueError(msg)

    base_sha = _nested_str(pull_request, ("base", "sha"))
    head_sha = _nested_str(pull_request, ("head", "sha"))
    if base_sha is None or head_sha is None:
        msg = "Missing pull request base or head SHA in GitHub event payload."
        raise ValueError(msg)

    return _messages_from_git_log([f"{base_sha}..{head_sha}"])


def _nested_str(data: dict[str, Any], keys: Sequence[str]) -> str | None:
    value: Any = data
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value if isinstance(value, str) else None


def _messages_from_git_log(revisions: Sequence[str]) -> list[CommitMessage]:
    git = shutil.which("git")
    if git is None:
        msg = "git executable was not found on PATH."
        raise RuntimeError(msg)

    completed = subprocess.run(  # noqa: S603
        [git, "log", f"--format=%H{FIELD_SEPARATOR}%B{RECORD_SEPARATOR}", *revisions],
        check=True,
        capture_output=True,
        text=True,
    )
    return _parse_git_log(completed.stdout)


def _parse_git_log(output: str) -> list[CommitMessage]:
    messages: list[CommitMessage] = []
    for raw_record in output.split(RECORD_SEPARATOR):
        record = raw_record.strip("\n")
        if not record:
            continue
        if FIELD_SEPARATOR not in record:
            msg = "Unexpected git log output format."
            raise ValueError(msg)
        commit, message = record.split(FIELD_SEPARATOR, 1)
        messages.append(CommitMessage(commit, message.strip("\n")))
    return messages


def _validate_message(message: str) -> list[str]:
    lines = message.splitlines()
    errors: list[str] = []
    if not lines or not message.strip():
        return ["Message must not be empty."]

    title = lines[0]
    if len(title) > MAX_TITLE_LENGTH:
        errors.append(f"Title must be {MAX_TITLE_LENGTH} characters or fewer.")
    if not TITLE_PATTERN.fullmatch(title):
        types = ", ".join(ALLOWED_TYPES)
        errors.append(
            "Title must use '<type>: <summary>' or '<type>(scope): <summary>' "
            f"with one of: {types}."
        )

    if len(lines) < 3:
        errors.append("Message must include a blank line followed by a body.")
        return errors

    if lines[1] != "":
        errors.append("Line 2 must be blank.")
    if not any(line.strip() for line in lines[2:]):
        errors.append("Body must contain at least one non-empty line.")

    for line_number, line in enumerate(lines[2:], start=3):
        if len(line) > MAX_BODY_LINE_LENGTH:
            errors.append(
                f"Body line {line_number} must be {MAX_BODY_LINE_LENGTH} characters or fewer."
            )

    return errors


def _print_failures(failures: Sequence[ValidationFailure]) -> None:
    print("Commit message validation failed:", file=sys.stderr)
    for failure in failures:
        print(f"\n{failure.label}:", file=sys.stderr)
        for error in failure.errors:
            print(f"- {error}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
