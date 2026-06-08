# -*- encoding: utf-8 -*-

"""
Phase 1.5 - P15-6 (CLI) tests.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from arcline.cli.main import app
from arcline.historian import (
    DSN_ENV_VAR,
    HistorySpec,
    cachePath,
    disposeEngine,
    writeCache,
)


@pytest.fixture(autouse = True)
def cleanEnv(monkeypatch):
    monkeypatch.delenv(DSN_ENV_VAR, raising = False)
    disposeEngine()
    yield
    disposeEngine()


def test_history_helpRegistered():
    runner = CliRunner()
    result = runner.invoke(app, ["history", "--help"])
    assert result.exit_code == 0
    assert "sync" in result.stdout
    assert "clear" in result.stdout
    assert "validate" in result.stdout


def test_history_validate_warnsWhenDsnUnset():
    runner = CliRunner()
    result = runner.invoke(app, ["history", "validate"])
    assert result.exit_code == 0
    combined = result.stdout + (result.stderr or "")
    assert "unreachable" in combined or "warehouse" in combined.lower()


def test_history_clear_emptyCacheReturnsZero(tmp_path):
    runner = CliRunner()
    result = runner.invoke(app, ["history", "clear", str(tmp_path)])
    assert result.exit_code == 0
    assert "cleared 0" in result.stdout


def test_history_clear_removesParquet(tmp_path):
    spec = HistorySpec(
        table = "t", keyColumn = "k", valueColumn = "v", tsColumn = "ts",
    )
    target = cachePath(tmp_path, "lane", "E", "x", spec, "2024-01-01", "2024-12-31")
    writeCache(target, pd.DataFrame({"ts": pd.to_datetime(["2024-01-01"]), "value": [1]}))

    runner = CliRunner()
    result = runner.invoke(app, ["history", "clear", str(tmp_path), "--kind", "lane"])
    assert result.exit_code == 0
    assert "cleared 1" in result.stdout


def test_history_sync_failsWhenDsnUnset(tmp_path, sampleProject):
    runner = CliRunner()
    result = runner.invoke(app, ["history", "sync", str(sampleProject.path)])
    assert result.exit_code == 2
    combined = result.stdout + (result.stderr or "")
    assert "warehouse" in combined.lower() or "ARCLINE_MSSQL_DSN" in combined
