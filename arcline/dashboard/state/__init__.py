# -*- encoding: utf-8 -*-

"""
Dashboard State Subpackage
==========================

Two distinct flavours of state live in the dashboard:

* **Client-side** ``dcc.Store`` keys defined in :mod:`store` - small,
  serialisable scalars (selected node hashKey, dirty flag, current
  visualization mode) shared between the browser and Dash callbacks.

* **Server-side** session state defined in :mod:`session` - the
  authoritative :class:`AbstractGraph` instance plus the associated
  :class:`arcline.io.Project` handle, mutated through a small command
  pattern that funnels every write through the backend graph mutators.
"""

from arcline.dashboard.state import session, store

__all__ = [
    "session",
    "store",
]
