# -*- encoding: utf-8 -*-

"""
Phase 1.5 - P15-2 (connection layer) tests.

These tests never touch a real MS-SQL Server. They cover:
  - DSN env-var discovery
  - DSN redaction (URL form + ODBC keyword form)
  - getEngine raising ConnectionError when DSN is unset
  - testConnection returning False (never raising) on any failure
  - getEngine memoizing one engine per process and disposeEngine resetting it
"""

from __future__ import annotations

import importlib
import os

import pytest

from arcline.historian import (
    DSN_ENV_VAR,
    ConnectionError,
    disposeEngine,
    getDsn,
    getEngine,
    redactDsn,
)
from arcline.historian import testConnection as probeConnection
from arcline.historian import connection as connModule


@pytest.fixture(autouse = True)
def cleanEngine(monkeypatch):
    monkeypatch.delenv(DSN_ENV_VAR, raising = False)
    disposeEngine()
    yield
    disposeEngine()


def test_redactDsn_urlForm():
    out = redactDsn("mssql+pyodbc://alice:s3cret@host/db")
    assert "s3cret" not in out
    assert "alice" in out
    assert "***" in out


def test_redactDsn_odbcKeywordForm():
    out = redactDsn("DRIVER={X};SERVER=h;UID=alice;PWD=s3cret;")
    assert "s3cret" not in out
    assert "***" in out
    assert "alice" in out


def test_redactDsn_unsetReturnsPlaceholder():
    assert redactDsn(None) == "<unset>"
    assert redactDsn("") == "<unset>"


def test_getDsn_unsetReturnsNone(monkeypatch):
    monkeypatch.delenv(DSN_ENV_VAR, raising = False)
    assert getDsn() is None


def test_getDsn_emptyTreatedAsUnset(monkeypatch):
    monkeypatch.setenv(DSN_ENV_VAR, "   ")
    assert getDsn() is None


def test_getEngine_raisesWhenDsnUnset():
    with pytest.raises(ConnectionError) as exc:
        getEngine()
    assert DSN_ENV_VAR in str(exc.value)


def test_testConnection_falseWhenDsnUnset():
    assert probeConnection() is False


def test_testConnection_falseOnEngineFailure(monkeypatch):
    monkeypatch.setenv(DSN_ENV_VAR, "mssql+pyodbc://u:p@nonexistent.invalid/db")

    class _FakeEngine:
        def connect(self):
            raise RuntimeError("nope")
        def dispose(self):
            pass

    def fakeImport():
        class _Sql:
            @staticmethod
            def create_engine(*a, **kw):
                return _FakeEngine()
            @staticmethod
            def text(s):
                return s
        return _Sql

    monkeypatch.setattr(connModule, "_importSqlalchemy", fakeImport)
    assert probeConnection() is False


def test_getEngine_memoizes(monkeypatch):
    monkeypatch.setenv(DSN_ENV_VAR, "mssql+pyodbc://u:p@h/db")

    calls = {"n": 0}

    class _FakeEngine:
        def dispose(self):
            pass

    def fakeImport():
        class _Sql:
            @staticmethod
            def create_engine(*a, **kw):
                calls["n"] += 1
                return _FakeEngine()
            @staticmethod
            def text(s):
                return s
        return _Sql

    monkeypatch.setattr(connModule, "_importSqlalchemy", fakeImport)
    e1 = getEngine()
    e2 = getEngine()
    assert e1 is e2
    assert calls["n"] == 1
    disposeEngine()
    e3 = getEngine()
    assert e3 is not e1
    assert calls["n"] == 2
