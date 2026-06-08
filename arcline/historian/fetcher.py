# -*- encoding: utf-8 -*-

"""
Historian Fetcher
-----------------

Composes a fully-parameterized ``SELECT`` from a :class:`HistorySpec`,
binds the entity ``hashKey`` and date range, and returns a tidy
:class:`pandas.DataFrame` with columns ``[ts, value]`` (plus any extra
columns from the spec's static filters).

All SQL is built via SQLAlchemy Core's ``text()`` / ``select()`` API,
never via f-string concatenation, so the warehouse cannot be tricked
into executing user-controlled SQL through ``filters``.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional, Union

from arcline.historian.cache import cachePath, readCache, writeCache, DateLike
from arcline.historian.connection import getEngine
from arcline.historian.exceptions import EmptyHistoryError
from arcline.historian.spec import HistorySpec
from arcline.utils.logging import getLogger

_log = getLogger(__name__)


def _importPandas() -> Any:
    import pandas as pd
    return pd


def _importSqlalchemy() -> Any:
    import sqlalchemy
    return sqlalchemy


def buildQuery(spec: HistorySpec) -> tuple[str, dict[str, Any]]:
    """
    Compose a parameterized SQL string for ``spec``.

    Returns ``(sqlText, staticParams)``. Caller binds ``hashKey``,
    ``start``, ``end`` plus the static-filter values (returned as
    ``staticParams`` so the caller can merge them at execute time).

    Static filter keys are validated against an identifier whitelist
    (``[A-Za-z_][A-Za-z0-9_]*``) before being interpolated; values are
    always parameterized.
    """
    import re as _re

    identRe = _re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

    for col in (spec.keyColumn, spec.valueColumn, spec.tsColumn):
        if not identRe.match(col):
            raise ValueError(f"invalid column identifier {col!r}")
    if spec.schema_ and not identRe.match(spec.schema_):
        raise ValueError(f"invalid schema identifier {spec.schema_!r}")
    tableParts = spec.table.split(".")
    for part in tableParts:
        if not identRe.match(part):
            raise ValueError(f"invalid table identifier {spec.table!r}")

    whereClauses = [
        f"{spec.keyColumn} = :hashKey",
        f"{spec.tsColumn} BETWEEN :start AND :end",
    ]
    staticParams: dict[str, Any] = {}
    for index, (column, value) in enumerate(spec.filters.items()):
        if not identRe.match(column):
            raise ValueError(f"invalid filter column {column!r}")
        bindName = f"flt_{index}"
        whereClauses.append(f"{column} = :{bindName}")
        staticParams[bindName] = value

    sql = (
        f"SELECT {spec.tsColumn} AS ts, {spec.valueColumn} AS value "
        f"FROM {spec.qualifiedTable()} "
        f"WHERE {' AND '.join(whereClauses)} "
        f"ORDER BY {spec.tsColumn} ASC"
    )
    return sql, staticParams


def fetch(
    *,
    projectPath: Path,
    kind: str,
    hashKey: str,
    attribute: str,
    spec: HistorySpec,
    start: DateLike,
    end: DateLike,
    refresh: bool = False,
    raiseOnEmpty: bool = False,
) -> Any:
    """
    Return historic ``[ts, value]`` rows for an entity attribute.

    Cache-first: a hit is returned without touching the warehouse. On
    a miss (or ``refresh=True``) the warehouse is queried, the result
    is persisted to Parquet, and the DataFrame is returned.

    :raises EmptyHistoryError: When the warehouse returns zero rows
        and ``raiseOnEmpty=True``.
    """
    pd = _importPandas()
    target = cachePath(projectPath, kind, hashKey, attribute, spec, start, end)

    if not refresh:
        cached = readCache(target)
        if cached is not None:
            _log.debug("historian cache hit", extra = {"path": str(target)})
            return cached

    sqlalchemy = _importSqlalchemy()
    engine = getEngine()
    sql, staticParams = buildQuery(spec)
    binds = {
        "hashKey": hashKey,
        "start": start,
        "end": end,
        **staticParams,
    }
    _log.info(
        "historian fetch",
        extra = {"kind": kind, "hashKey": hashKey, "attribute": attribute},
    )
    with engine.connect() as conn:
        frame = pd.read_sql(sqlalchemy.text(sql), conn, params = binds)

    if frame.empty and raiseOnEmpty:
        raise EmptyHistoryError(
            f"no rows for {kind}/{hashKey}/{attribute} in [{start}, {end}]"
        )

    if "ts" in frame.columns:
        frame["ts"] = pd.to_datetime(frame["ts"])
    writeCache(target, frame)
    return frame
