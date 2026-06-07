# -*- encoding: utf-8 -*-

"""
Structured Logging Configuration
--------------------------------

Process-wide logging helpers used across the :mod:`arcline` package.
The :func:`configure_logging` entry point is idempotent and safe to
call multiple times; :func:`get_logger` lazily triggers a default
configuration the first time a logger is requested.

A small :class:`CredentialsRedactor` filter is wired into the root
logger so that future :mod:`arcline.historian` MS-SQL DSNs cannot
accidentally leak through log output (the filter rewrites
``mssql+pyodbc://...`` substrings to ``mssql+pyodbc://***``).
"""

import json
import logging
import os
import re


DEFAULT_FORMAT : str = (
    "%(asctime)s [%(levelname)s] %(name)s :: %(message)s"
)

_CONFIGURED : bool = False
_DSN_PATTERN : re.Pattern = re.compile(r"mssql\+pyodbc://[^\"\s]+")


class JsonFormatter(logging.Formatter):
    """
    Minimal JSON line formatter emitting ``{"ts", "level", "name",
    "msg"}`` records on a single line. Used when
    :func:`configure_logging` is called with ``json=True`` for
    log-aggregator-friendly output.
    """

    def format(self, record : logging.LogRecord) -> str:
        """
        Render ``record`` as a single-line JSON string.

        :type  record: logging.LogRecord
        :param record: Standard logging record produced by the root
            logger.

        :rtype:   str
        :returns: A JSON-encoded one-line representation of the
            record.
        """

        payload : dict = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "msg": record.getMessage(),
        }

        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii = False, default = str)


class CredentialsRedactor(logging.Filter):
    """
    Logging filter that rewrites MS-SQL connection strings appearing
    in a log message to a redacted placeholder. Applied at the root
    logger level so every downstream handler sees the redacted form.
    """

    def filter(self, record : logging.LogRecord) -> bool:
        """
        Mutate ``record.msg`` (and clear ``record.args``) to redact
        any embedded MS-SQL DSN substring.

        :type  record: logging.LogRecord
        :param record: The logging record to inspect and mutate.

        :rtype:   bool
        :returns: Always ``True`` so the record continues to flow.
        """

        try:
            message = record.getMessage()
        except Exception:
            return True

        if "mssql+pyodbc://" in message:
            record.msg = _DSN_PATTERN.sub(
                "mssql+pyodbc://***", message
            )
            record.args = None

        return True


def configure_logging(level : str = "INFO", json : bool = False) -> None:
    """
    Idempotent root-logger configuration. Safe to call multiple
    times in a single process; subsequent calls are no-ops unless
    the sentinel ``_CONFIGURED`` flag is reset by tests.

    The effective level honours the ``ARCLINE_LOG_LEVEL`` environment
    variable when set, overriding the ``level`` argument. Output goes
    to ``stderr`` via a single :class:`logging.StreamHandler`.

    :type  level: str
    :param level: Default level name (``"DEBUG"``, ``"INFO"``,
        ``"WARNING"``, ``"ERROR"``, ``"CRITICAL"``).

    :type  json: bool
    :param json: When ``True`` use :class:`JsonFormatter` instead of
        the human-readable :data:`DEFAULT_FORMAT`.

    :rtype:   None
    """

    global _CONFIGURED

    if _CONFIGURED:
        return

    env_level = os.environ.get("ARCLINE_LOG_LEVEL")
    effective : str = env_level.upper() if env_level else level.upper()

    root = logging.getLogger()
    root.setLevel(getattr(logging, effective, logging.INFO))

    handler = logging.StreamHandler()
    if json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(DEFAULT_FORMAT))

    root.addFilter(CredentialsRedactor())
    root.addHandler(handler)

    _CONFIGURED = True


def get_logger(name : str) -> logging.Logger:
    """
    Return a child logger by name, lazily triggering a default
    :func:`configure_logging` call if the root logger has not been
    configured yet.

    :type  name: str
    :param name: Dotted logger name (typically ``__name__`` of the
        calling module).

    :rtype:   logging.Logger
    :returns: A configured child :class:`logging.Logger` instance.
    """

    if not _CONFIGURED:
        configure_logging()

    return logging.getLogger(name)


def __reset_for_tests__() -> None:
    """
    Reset the module-level ``_CONFIGURED`` sentinel so that test
    fixtures can re-exercise :func:`configure_logging`. Production
    code should not need this hook.

    :rtype:   None
    """

    global _CONFIGURED
    _CONFIGURED = False
