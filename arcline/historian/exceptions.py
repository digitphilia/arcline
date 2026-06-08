# -*- encoding: utf-8 -*-

"""
Historian Exceptions
--------------------

Dedicated exception hierarchy for :mod:`arcline.historian` so callers
(CLI, dashboard, third-party scripts) can ``except`` on a stable type
rather than string-matching error messages.
"""

from __future__ import annotations


class HistorianError(Exception):
    """Base class for every historian-layer failure."""


class ConnectionError(HistorianError):  # noqa: A001 - shadows builtin intentionally within historian ns
    """Raised when the MS-SQL engine cannot be created or reached."""


class SpecError(HistorianError):
    """Raised when a :class:`HistorySpec` is invalid or missing."""


class EmptyHistoryError(HistorianError):
    """Raised when a fetch returns zero rows for a non-optional request."""


class CacheError(HistorianError):
    """Raised when the on-disk Parquet cache cannot be read or written."""
