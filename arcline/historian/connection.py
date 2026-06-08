# -*- encoding: utf-8 -*-

"""
Historian Connection Layer
--------------------------

Thin facade around SQLAlchemy Core that owns a single, lazily-initialized
engine pointing at the MS-SQL Server data warehouse described by the
``ARCLINE_MSSQL_DSN`` environment variable.

Design tenets
~~~~~~~~~~~~~

* **No DSN ever appears in logs, manifests, or cache files.** The DSN
  is read from the environment, never serialized; redaction is enforced
  by ``redactDsn`` for any caller that needs to surface diagnostics.
* **Lazy initialization.** Importing this module does not require
  SQLAlchemy or pyodbc; the heavy imports happen on the first call to
  :func:`getEngine`. Users without the ``[historian]`` extra installed
  can still load projects and use the dashboard's offline (cached) mode.
* **Single process-wide pool.** SQLAlchemy's connection pool is the
  source of truth; we do not re-pool on top.
* **Optional dependency safety.** If ``sqlalchemy`` or ``pyodbc`` are
  missing, calls raise :class:`ConnectionError` with a clear remediation
  message instead of an opaque ``ImportError``.
"""

from __future__ import annotations

import os
import re
import threading
from typing import Any, Optional

from arcline.historian.exceptions import ConnectionError as _ConnectionError
from arcline.utils.logging import getLogger

DSN_ENV_VAR : str = "ARCLINE_MSSQL_DSN"

_engineLock = threading.Lock()
_engine : Any = None
_log = getLogger(__name__)


def _importSqlalchemy() -> Any:
    """Import :mod:`sqlalchemy` lazily; raise ``ConnectionError`` if missing."""
    try:
        import sqlalchemy  # type: ignore[import-not-found]
        return sqlalchemy
    except ImportError as exc:
        raise _ConnectionError(
            "sqlalchemy is not installed. Install the historian extra: "
            "pip install 'arcline[historian]'."
        ) from exc


def redactDsn(dsn: Optional[str]) -> str:
    """
    Return ``dsn`` with the password component masked.

    Accepts ``mssql+pyodbc://user:password@host/db`` style URLs and the
    ODBC keyword form (``DRIVER=...;PWD=secret;...``). The output is
    always safe to log.
    """
    if not dsn:
        return "<unset>"
    redacted = re.sub(r"(://[^:/@]+:)[^@/]+(@)", r"\1***\2", dsn)
    redacted = re.sub(
        r"(?i)(\b(?:PWD|PASSWORD)\s*=\s*)([^;]+)", r"\1***", redacted,
    )
    return redacted


def getDsn() -> Optional[str]:
    """Return the DSN from the environment, or ``None`` if unset/empty."""
    value = os.environ.get(DSN_ENV_VAR, "").strip()
    return value or None


def getEngine(echo: bool = False) -> Any:
    """
    Return the process-wide SQLAlchemy engine, creating it on first call.

    :raises ConnectionError: If ``ARCLINE_MSSQL_DSN`` is unset or the
        SQLAlchemy / pyodbc dependencies are not installed.
    """
    global _engine
    if _engine is not None:
        return _engine

    with _engineLock:
        if _engine is not None:
            return _engine

        dsn = getDsn()
        if dsn is None:
            raise _ConnectionError(
                f"Environment variable {DSN_ENV_VAR} is not set; the "
                f"historian cannot reach MS-SQL Server. Set it to a "
                f"valid SQLAlchemy URL, e.g. "
                f"'mssql+pyodbc://user:pass@host/db?driver=ODBC+Driver+18+for+SQL+Server'."
            )

        sqlalchemy = _importSqlalchemy()
        _log.info("creating historian engine", extra = {"dsn": redactDsn(dsn)})
        try:
            _engine = sqlalchemy.create_engine(
                dsn, echo = echo, future = True, pool_pre_ping = True,
            )
        except Exception as exc:
            raise _ConnectionError(
                f"Failed to create SQLAlchemy engine for "
                f"{redactDsn(dsn)!r}: {exc}"
            ) from exc
        return _engine


def testConnection(timeout: float = 5.0) -> bool:
    """
    Probe the warehouse with a trivial ``SELECT 1``.

    Returns ``True`` on success, ``False`` on any failure (missing DSN,
    missing driver, network error, auth error). Never raises.

    The dashboard's DB-status pill uses this to decide between green
    (connected), amber (cached-only fallback), and red (unreachable).
    """
    try:
        sqlalchemy = _importSqlalchemy()
        engine = getEngine()
    except _ConnectionError:
        return False

    try:
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))
        return True
    except Exception as exc:
        _log.warning(
            "historian testConnection failed",
            extra = {"error": str(exc)},
        )
        return False


def disposeEngine() -> None:
    """Dispose the process-wide engine and close all pooled connections."""
    global _engine
    with _engineLock:
        if _engine is not None:
            try:
                _engine.dispose()
            finally:
                _engine = None
