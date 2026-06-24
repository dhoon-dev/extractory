from __future__ import annotations

import runpy
from collections.abc import Callable
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = runpy.run_path(str(ROOT / "scripts" / "check_commit_messages.py"))
validate_message: Callable[[str], list[str]] = MODULE["_validate_message"]


def test_valid_commit_message_passes() -> None:
    message = (
        "fix: preserve live API default\n"
        "\n"
        "Ensure empty optional CI variables do not override the SDK default\n"
        "base URL during live tests."
    )

    assert validate_message(message) == []


@pytest.mark.parametrize(
    ("message", "expected_error"),
    [
        (
            "fix: preserve live API default",
            "Message must include a blank line followed by a body.",
        ),
        (
            "style: preserve live API default\n\nExplain the change.",
            "Title must use '<type>: <summary>'",
        ),
        (
            "fix: this title is too long for the repository commit rule\n\nExplain the change.",
            "Title must be 50 characters or fewer.",
        ),
        (
            "fix: preserve live API default\n"
            "\n"
            "This body line is intentionally longer than seventy-two characters so it fails.",
            "Body line 3 must be 72 characters or fewer.",
        ),
    ],
)
def test_invalid_commit_messages_report_errors(message: str, expected_error: str) -> None:
    errors = validate_message(message)

    assert any(expected_error in error for error in errors)
