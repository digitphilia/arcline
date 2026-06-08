# -*- encoding: utf-8 -*-

"""
Backward-compatible re-export of :class:`arcline_d3.NetworkCanvas`.

The authoritative class definition now lives in the top-level
:mod:`arcline_d3` package — this is a hard requirement of Dash's
:class:`~dash.development.base_component.ComponentMeta`, which keys
its component registry on ``cls.__module__.split(".")[0]``. Defining
the class anywhere under :mod:`arcline.*` would mis-register the
suite under the ``arcline`` namespace, breaking
``/_dash-component-suites/arcline_d3/arcline_d3.js`` service.

This shim exists purely so existing imports such as
``from arcline.dashboard.d3 import NetworkCanvas`` keep working.
"""

from arcline_d3 import NetworkCanvas

__all__ = ["NetworkCanvas"]
