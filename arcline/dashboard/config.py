# -*- encoding: utf-8 -*-

"""
Dashboard Configuration Settings
--------------------------------

A small :mod:`pydantic-settings` driven configuration model that holds
runtime knobs for the Dash dashboard (project path, host, port, debug
flag, bootstrap theme, cache directory). All fields can be overridden
via environment variables prefixed with ``ARCLINE_`` (for example,
``ARCLINE_HOST``, ``ARCLINE_PORT``) which keeps the dashboard
12-factor friendly.

The :func:`getSettings` convenience wrapper caches a single shared
:class:`DashboardSettings` instance for the lifetime of the process
so that callers can read configuration without having to thread an
explicit settings object through every helper.
"""

import functools
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DashboardSettings(BaseSettings):
    """
    Pydantic-settings driven dashboard configuration.

    :param projectPath: Optional path to the project directory that
        the dashboard should bind to on startup.

    :param host: Bind host for the underlying Flask server; defaults
        to ``"127.0.0.1"`` for localhost-only operation.

    :param port: TCP port to listen on; constrained to the
        unprivileged range ``[1024, 65535]``.

    :param debug: Enable Dash hot-reload and verbose tracebacks.

    :param theme: Name of the :mod:`dash-bootstrap-components` theme
        to apply (for example ``"BOOTSTRAP"``, ``"FLATLY"``,
        ``"DARKLY"``).

    :param cacheDir: Optional explicit cache directory for the
        :mod:`flask-caching` filesystem backend; defaults to
        ``<projectPath>/.cache/dash/`` when a project is bound.
    """

    model_config = SettingsConfigDict(
        env_prefix = "ARCLINE_", extra = "ignore"
    )

    projectPath : Optional[Path] = Field(None)
    host : str = Field("127.0.0.1")
    port : int = Field(8050, ge = 1024, le = 65535)
    debug : bool = Field(False)
    theme : str = Field("BOOTSTRAP")
    cacheDir : Optional[Path] = Field(None)


@functools.lru_cache(maxsize = 1)
def getSettings() -> DashboardSettings:
    """
    Return a process-wide cached :class:`DashboardSettings` instance.

    The first invocation constructs a fresh :class:`DashboardSettings`
    from environment variables; subsequent calls return the same
    cached object. Tests that need a clean settings snapshot should
    call :func:`getSettings.cache_clear` before reading.

    :rtype:   DashboardSettings
    :returns: The cached settings singleton.
    """

    return DashboardSettings()
