# -*- encoding: utf-8 -*-

"""
arcline.historian
-----------------

Phase 1.5 historic-data layer: pulls time-series for any node/edge
attribute from a MS-SQL Server data warehouse, caches the result as
local Parquet, and exposes baseline univariate analytics.

Foundation (P15-1) ships only :class:`HistorySpec`, :class:`HistorianMixin`,
and the exception hierarchy. Connection, fetcher, cache, analytics,
CLI, and dashboard wiring land in P15-2..P15-7.
"""

from arcline.historian.exceptions import (
    HistorianError,
    ConnectionError,
    SpecError,
    EmptyHistoryError,
    CacheError,
)
from arcline.historian.spec import HistorySpec, HistorianMixin, Aggregation
from arcline.historian.connection import (
    DSN_ENV_VAR,
    getDsn,
    getEngine,
    testConnection,
    disposeEngine,
    redactDsn,
)
from arcline.historian.cache import (
    cacheRoot,
    cachePath,
    readCache,
    writeCache,
    clearCache,
)
from arcline.historian.fetcher import fetch, buildQuery
from arcline.historian.analytics import summary, rolling, distribution, resample

__all__ = [
    "HistorianError",
    "ConnectionError",
    "SpecError",
    "EmptyHistoryError",
    "CacheError",
    "HistorySpec",
    "HistorianMixin",
    "Aggregation",
    "DSN_ENV_VAR",
    "getDsn",
    "getEngine",
    "testConnection",
    "disposeEngine",
    "redactDsn",
    "cacheRoot",
    "cachePath",
    "readCache",
    "writeCache",
    "clearCache",
    "fetch",
    "buildQuery",
    "summary",
    "rolling",
    "distribution",
    "resample",
]
