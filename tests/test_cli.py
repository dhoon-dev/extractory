from typer.testing import CliRunner

from extractory.cli import app


def test_cli_help_works() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Extractory" in result.output


def test_jira_help_works() -> None:
    result = CliRunner().invoke(app, ["jira", "--help"])

    assert result.exit_code == 0
    assert "Jira" in result.output


def test_gerrit_help_works() -> None:
    result = CliRunner().invoke(app, ["gerrit", "--help"])

    assert result.exit_code == 0
    assert "Gerrit" in result.output
