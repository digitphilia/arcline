# -*- encoding: utf-8 -*-

"""
Utility Helpers
===============

Small, dependency-light helpers shared across the :mod:`arcline`
package: deterministic identifier generation, structured logging
configuration, and basic geographic distance/bounding-box math.
"""

from arcline.utils.hashing import make_key, make_node_key, make_edge_key
from arcline.utils.logging import configure_logging, get_logger
from arcline.utils.geo import haversine, bbox

__all__ = [
    "make_key",
    "make_node_key",
    "make_edge_key",
    "configure_logging",
    "get_logger",
    "haversine",
    "bbox",
]
