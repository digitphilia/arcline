# -*- encoding: utf-8 -*-

"""
Dashboard Flask Server Factory
------------------------------

Builds the underlying :class:`flask.Flask` instance that hosts the
Dash application. The server is configured with a
:mod:`flask-caching` ``FileSystemCache`` rooted under the project's
``.cache/dash/`` directory so that long-running callback computations
can be memoised across requests.

A module-level :data:`_CACHE` slot exposes the active cache to other
dashboard components through :func:`getCache`; this avoids passing
the cache around as an explicit dependency to every callback module.

:NOTE: The ``SECRET_KEY`` is sourced from the
``ARCLINE_DASHBOARD_SECRET`` environment variable when present and
generated as an ephemeral random token otherwise (with a warning
emitted on the package logger).
"""

import os
import secrets
from pathlib import Path
from typing import Optional

from flask import Flask
from flask_caching import Cache

from arcline.dashboard.config import DashboardSettings
from arcline.utils.logging import getLogger


_CACHE : Optional[Cache] = None
_LOGGER = getLogger("arcline.dashboard.server")


def __resolve_cache_dir__(settings : DashboardSettings) -> Path:
    """
    Resolve the cache directory using the priority order of explicit
    ``cacheDir`` setting, then per-project ``.cache/dash/``, then a
    process-local fallback under the current working directory.

    :type  settings: DashboardSettings
    :param settings: The active dashboard settings.

    :rtype:   Path
    :returns: The resolved cache directory path (parent directories
        are created if they do not already exist).
    """

    if settings.cacheDir is not None:
        target = Path(settings.cacheDir)
    elif settings.projectPath is not None:
        target = Path(settings.projectPath) / ".cache" / "dash"
    else:
        target = Path.cwd() / ".cache" / "dash"

    target.mkdir(parents = True, exist_ok = True)
    return target


def createServer(settings : DashboardSettings) -> Flask:
    """
    Construct the Flask server that hosts the Dash app.

    Initialises a :class:`flask_caching.Cache` backed by the local
    filesystem, attaches it to the application, and exposes it via
    :func:`getCache` for other dashboard subsystems to share.

    :type  settings: DashboardSettings
    :param settings: Resolved dashboard settings driving cache and
        secret-key configuration.

    :rtype:   Flask
    :returns: A configured :class:`flask.Flask` instance ready to be
        attached to a :class:`dash.Dash` application.
    """

    global _CACHE

    server = Flask("arcline.dashboard")

    secret = os.environ.get("ARCLINE_DASHBOARD_SECRET")
    if not secret:
        secret = secrets.token_hex(32)
        _LOGGER.warning(
            "ARCLINE_DASHBOARD_SECRET not set; generated an ephemeral "
            "secret key for this process. Sessions will not survive "
            "a restart."
        )
    server.config["SECRET_KEY"] = secret

    cacheDir = __resolve_cache_dir__(settings)
    cache = Cache(
        server,
        config = {
            "CACHE_TYPE": "FileSystemCache",
            "CACHE_DIR": str(cacheDir),
            "CACHE_DEFAULT_TIMEOUT": 300,
        },
    )
    _CACHE = cache

    return server


def getCache() -> Cache:
    """
    Return the active :class:`flask_caching.Cache` instance.

    :raises RuntimeError: If :func:`createServer` has not yet been
        called in the current process.

    :rtype:   Cache
    :returns: The shared cache attached to the dashboard's Flask app.
    """

    if _CACHE is None:
        raise RuntimeError(
            "Flask cache not initialised; call createServer() first."
        )

    return _CACHE
