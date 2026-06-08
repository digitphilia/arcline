# -*- encoding: utf-8 -*-

"""
Utility Helpers
===============

Small, dependency-light helpers shared across the :mod:`arcline`
package: deterministic identifier generation, structured logging
configuration, and basic geographic distance/bounding-box math.
"""

from arcline.utils.hashing import makeKey, makeNodeKey, makeEdgeKey
from arcline.utils.logging import configureLogging, getLogger
from arcline.utils.geo import haversine, bbox

import warnings as _warnings


def _deprecated(oldName, new):
    def _shim(*args, **kwargs):
        _warnings.warn(
            f"arcline.utils.{oldName}() is deprecated; "
            f"use arcline.utils.{new.__name__}() instead.",
            DeprecationWarning,
            stacklevel = 2,
        )
        return new(*args, **kwargs)
    _shim.__name__ = oldName
    _shim.__doc__ = f"Deprecated alias of :func:`{new.__name__}`."
    return _shim


make_key = _deprecated("make_key", makeKey)
make_node_key = _deprecated("make_node_key", makeNodeKey)
make_edge_key = _deprecated("make_edge_key", makeEdgeKey)
configure_logging = _deprecated("configure_logging", configureLogging)
get_logger = _deprecated("get_logger", getLogger)


__all__ = [
    "makeKey",
    "makeNodeKey",
    "makeEdgeKey",
    "configureLogging",
    "getLogger",
    "haversine",
    "bbox",
    # Deprecated snake_case aliases (removed in 0.2.0):
    "make_key",
    "make_node_key",
    "make_edge_key",
    "configure_logging",
    "get_logger",
]
