# -*- encoding: utf-8 -*-

"""
Phase 1.5 - P15-3 (fetcher + cache) tests.

No live MS-SQL is required. Engine is patched to a fake that returns a
canned DataFrame; SQL composition is asserted on the rendered string;
cache hit/miss/invalidate paths are exercised against tmp_path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from arcline.historian import (
    DSN_ENV_VAR,
    HistorySpec,
    buildQuery,
    cachePath,
    clearCache,
    disposeEngine,
    fetch,
    readCache,
    writeCache,
)
from arcline.historian import connection as connModule
from arcline.historian import fetcher as fetcherModule


def makeSpec(**kw) -> HistorySpec:
    base = dict(
        table = "fact_lane_lead_time",
        keyColumn = "edge_hash_key",
        valueColumn = "actual_lead_time_days",
        tsColumn = "shipment_date",
    )
    base.update(kw)
    return HistorySpec(**base)


@pytest.fixture(autouse = True)
def cleanEngine(monkeypatch):
    monkeypatch.delenv(DSN_ENV_VAR, raising = False)
    disposeEngine()
    yield
    disposeEngine()


# -- buildQuery --------------------------------------------------------

def test_buildQuery_basicSelect():
    sql, params = buildQuery(makeSpec())
    assert "SELECT shipment_date AS ts" in sql
    assert "actual_lead_time_days AS value" in sql
    assert "FROM fact_lane_lead_time" in sql
    assert "edge_hash_key = :hashKey" in sql
    assert "shipment_date BETWEEN :start AND :end" in sql
    assert "ORDER BY shipment_date ASC" in sql
    assert params == {}


def test_buildQuery_qualifiesSchema():
    sql, _ = buildQuery(makeSpec(schema = "dwh"))
    assert "FROM dwh.fact_lane_lead_time" in sql


def test_buildQuery_filtersAreParameterized():
    sql, params = buildQuery(makeSpec(filters = {"is_active": 1, "region": "EU"}))
    assert "is_active = :flt_0" in sql
    assert "region = :flt_1" in sql
    assert params == {"flt_0": 1, "flt_1": "EU"}


def test_buildQuery_rejectsSqlInjectionInIdentifiers():
    with pytest.raises(ValueError):
        buildQuery(makeSpec(table = "t; DROP TABLE x"))
    with pytest.raises(ValueError):
        buildQuery(makeSpec(filters = {"x; DROP TABLE y": 1}))
    with pytest.raises(ValueError):
        buildQuery(makeSpec(valueColumn = "v) UNION SELECT *"))


# -- cache primitives --------------------------------------------------

def test_cachePath_includesSpecHash(tmp_path):
    spec = makeSpec()
    p = cachePath(tmp_path, "lane", "E-S1P1", "leadTimeDays", spec, "2024-01-01", "2024-12-31")
    assert spec.specHash() in p.name
    assert p.parent.parent.name == "lane"
    assert p.parent.name == "E-S1P1"


def test_cachePath_changesOnSpecDrift(tmp_path):
    a = cachePath(tmp_path, "lane", "E", "x", makeSpec(), "2024-01-01", "2024-12-31")
    b = cachePath(tmp_path, "lane", "E", "x", makeSpec(valueColumn = "other"), "2024-01-01", "2024-12-31")
    assert a != b


def test_writeReadCache_roundtrip(tmp_path):
    target = tmp_path / "history" / "lane" / "E" / "x.parquet"
    frame = pd.DataFrame({"ts": pd.to_datetime(["2024-01-01"]), "value": [1.5]})
    writeCache(target, frame)
    out = readCache(target)
    assert out is not None
    assert list(out.columns) == ["ts", "value"]


def test_readCache_returnsNoneOnMiss(tmp_path):
    assert readCache(tmp_path / "missing.parquet") is None


def test_clearCache_scoped(tmp_path):
    spec = makeSpec()
    for kind, key in [("lane", "E1"), ("lane", "E2"), ("plant", "P1")]:
        target = cachePath(tmp_path, kind, key, "x", spec, "2024-01-01", "2024-12-31")
        writeCache(target, pd.DataFrame({"ts": pd.to_datetime(["2024-01-01"]), "value": [1]}))
    assert clearCache(tmp_path, "lane", "E1") == 1
    assert clearCache(tmp_path, "lane") == 1  # E2 remains
    assert clearCache(tmp_path) == 1  # plant/P1


# -- fetch (engine mocked) ---------------------------------------------

class _FakeConn:
    def __init__(self, frame): self._frame = frame
    def __enter__(self): return self
    def __exit__(self, *a): pass


class _FakeEngine:
    def __init__(self, frame): self._frame = frame
    def connect(self): return _FakeConn(self._frame)
    def dispose(self): pass


def _patchEngine(monkeypatch, frame):
    fakeEngine = _FakeEngine(frame)

    class _Sql:
        @staticmethod
        def create_engine(*a, **kw): return fakeEngine
        @staticmethod
        def text(s): return s

    monkeypatch.setattr(connModule, "_importSqlalchemy", lambda: _Sql)
    monkeypatch.setattr(fetcherModule, "_importSqlalchemy", lambda: _Sql)

    def fakeReadSql(sqlText, conn, params=None):
        return frame.copy()

    monkeypatch.setattr(
        fetcherModule, "_importPandas",
        lambda: type("P", (), {
            "read_sql": staticmethod(fakeReadSql),
            "to_datetime": staticmethod(pd.to_datetime),
        }),
    )


def test_fetch_writesCacheOnMiss(tmp_path, monkeypatch):
    monkeypatch.setenv(DSN_ENV_VAR, "mssql+pyodbc://u:p@h/db")
    frame = pd.DataFrame({"ts": ["2024-01-01", "2024-02-01"], "value": [1.0, 2.0]})
    _patchEngine(monkeypatch, frame)

    spec = makeSpec()
    out = fetch(
        projectPath = tmp_path, kind = "lane", hashKey = "E-S1P1",
        attribute = "leadTimeDays", spec = spec,
        start = "2024-01-01", end = "2024-12-31",
    )
    assert len(out) == 2
    target = cachePath(tmp_path, "lane", "E-S1P1", "leadTimeDays", spec, "2024-01-01", "2024-12-31")
    assert target.exists()


def test_fetch_returnsCacheOnHit(tmp_path, monkeypatch):
    monkeypatch.setenv(DSN_ENV_VAR, "mssql+pyodbc://u:p@h/db")
    spec = makeSpec()
    target = cachePath(tmp_path, "lane", "E", "x", spec, "2024-01-01", "2024-12-31")
    cached = pd.DataFrame({"ts": pd.to_datetime(["2024-01-01"]), "value": [42.0]})
    writeCache(target, cached)

    def boom():
        raise AssertionError("engine should not be touched on cache hit")
    monkeypatch.setattr(fetcherModule, "_importSqlalchemy", boom)
    monkeypatch.setattr(fetcherModule, "_importPandas", lambda: pd)

    out = fetch(
        projectPath = tmp_path, kind = "lane", hashKey = "E",
        attribute = "x", spec = spec,
        start = "2024-01-01", end = "2024-12-31",
    )
    assert out["value"].iloc[0] == 42.0


def test_fetch_refreshBypassesCache(tmp_path, monkeypatch):
    monkeypatch.setenv(DSN_ENV_VAR, "mssql+pyodbc://u:p@h/db")
    spec = makeSpec()
    target = cachePath(tmp_path, "lane", "E", "x", spec, "2024-01-01", "2024-12-31")
    writeCache(target, pd.DataFrame({"ts": pd.to_datetime(["2024-01-01"]), "value": [99.0]}))

    fresh = pd.DataFrame({"ts": ["2024-06-01"], "value": [7.0]})
    _patchEngine(monkeypatch, fresh)

    out = fetch(
        projectPath = tmp_path, kind = "lane", hashKey = "E",
        attribute = "x", spec = spec,
        start = "2024-01-01", end = "2024-12-31",
        refresh = True,
    )
    assert out["value"].iloc[0] == 7.0
