# -*- encoding: utf-8 -*-

"""
arcline.dashboard.d3 - Backward-compatible re-export package.

The authoritative :class:`NetworkCanvas` component now lives in the
top-level :mod:`arcline_d3` package (required by Dash's component
registry mechanism). This sub-package merely re-exports it so legacy
imports such as ``from arcline.dashboard.d3 import NetworkCanvas``
continue to work.
"""

from arcline_d3 import NetworkCanvas

__all__ = ["NetworkCanvas"]
