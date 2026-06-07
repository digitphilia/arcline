# -*- encoding: utf-8 -*-

"""
Tests for the arcline Command-Line Interface
--------------------------------------------

Exercises the friendly error paths exposed by
:mod:`arcline.cli.commands` via :class:`typer.testing.CliRunner` so
that operator-facing failures stay actionable rather than leaking
raw Python tracebacks.
"""

from pathlib import Path

from typer.testing import CliRunner

from arcline.cli.main import app


def test_cli_init_existing_path_friendly(tmp_path : Path) -> None:
    """Regression: a second ``init`` on the same path fails friendly."""

    runner = CliRunner()
    target = tmp_path / "smoke"

    first = runner.invoke(app, ["init", str(target), "--name", "smoke"])
    assert first.exit_code == 0

    second = runner.invoke(app, ["init", str(target), "--name", "smoke"])
    assert second.exit_code == 1
    assert "already" in second.output.lower()
    assert "Traceback" not in second.output


def test_cli_validate_missing_path_friendly(tmp_path : Path) -> None:
    """Regression: ``validate`` on a non-existent path fails friendly."""

    runner = CliRunner()
    missing = tmp_path / "does_not_exist"

    result = runner.invoke(app, ["validate", str(missing)])
    assert result.exit_code != 0
    assert "not found" in result.output.lower()
    assert "Traceback" not in result.output
