# -*- encoding: utf-8 -*-

"""
Historian Parquet Cache
-----------------------

On-disk Parquet snapshot of historic fetches keyed by entity, attribute,
spec hash, and time range. Lives under ``<project>/.cache/history/`` and
is always gitignored (``arcline init`` writes the entry).

Cache key format::

    <project>/.cache/history/<kind>/<hashKey>/<attribute>__<specHash>__<start>_<end>.parquet

Including ``specHash`` in the filename makes spec drift (e.g. swapping a
``valueColumn``) automatically invalidate prior snapshots without
manual ``arcline history clear``.
"""

from __future__ import annotations

import shutil
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Union

from arcline.historian.exceptions import CacheError
from arcline.historian.spec import HistorySpec

DateLike = Union[str, date, datetime]


def _formatDate(value: DateLike) -> str:
    """Return ``YYYYMMDD`` for any date-like input."""
    if isinstance(value, datetime):
        return value.strftime("%Y%m%d")
    if isinstance(value, date):
        return value.strftime("%Y%m%d")
    text = str(value).strip()
    return text.replace("-", "").replace("/", "").replace(" ", "_")[:14]


def cacheRoot(projectPath: Path) -> Path:
    """Return ``<project>/.cache/history`` (does not create it)."""
    return Path(projectPath) / ".cache" / "history"


def cachePath(
    projectPath: Path,
    kind: str,
    hashKey: str,
    attribute: str,
    spec: HistorySpec,
    start: DateLike,
    end: DateLike,
) -> Path:
    """Return the Parquet path for a (entity, attribute, range) tuple."""
    name = f"{attribute}__{spec.specHash()}__{_formatDate(start)}_{_formatDate(end)}.parquet"
    return cacheRoot(projectPath) / kind / hashKey / name


def readCache(path: Path) -> Optional["pandas.DataFrame"]:  # type: ignore[name-defined]
    """Return the cached DataFrame for ``path`` or ``None`` on miss."""
    if not path.exists():
        return None
    try:
        import pandas as pd
        return pd.read_parquet(path)
    except Exception as exc:
        raise CacheError(f"failed to read cache {path!s}: {exc}") from exc


def writeCache(path: Path, frame: "pandas.DataFrame") -> None:  # type: ignore[name-defined]
    """Persist ``frame`` to ``path``, creating parent dirs as needed."""
    try:
        path.parent.mkdir(parents = True, exist_ok = True)
        frame.to_parquet(path, index = False)
    except Exception as exc:
        raise CacheError(f"failed to write cache {path!s}: {exc}") from exc


def clearCache(
    projectPath: Path,
    kind: Optional[str] = None,
    hashKey: Optional[str] = None,
) -> int:
    """
    Remove cached Parquet files; return the number of files deleted.

    Scope is progressively narrowed by the optional arguments:

    * ``clearCache(project)``                      -> entire history cache
    * ``clearCache(project, kind="lane")``         -> all lanes
    * ``clearCache(project, "lane", "E-S1P1")``    -> one specific edge
    """
    root = cacheRoot(Path(projectPath))
    if kind:
        root = root / kind
    if hashKey:
        root = root / hashKey
    if not root.exists():
        return 0
    deleted = sum(1 for _ in root.rglob("*.parquet"))
    shutil.rmtree(root)
    return deleted
