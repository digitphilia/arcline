# -*- encoding: utf-8 -*-

"""
HistorySpec Registry
--------------------

Cross-class lookup of :class:`HistorySpec` definitions by ``(kind, attribute)``
without requiring callers to know which concrete class registers a given kind.
The dashboard's history page uses this to drive the attribute dropdown.
"""

from __future__ import annotations

from typing import Iterable, Optional, Tuple

from arcline.historian.spec import HistorySpec


def _lookupClass(kind: str):
    from arcline.graph.registry import resolve_node, resolve_edge
    try:
        return resolve_node(kind)
    except Exception:
        try:
            return resolve_edge(kind)
        except Exception:
            return None


def specFor(kind: str, attribute: str) -> Optional[HistorySpec]:
    """Return the :class:`HistorySpec` for ``(kind, attribute)`` or ``None``."""
    cls = _lookupClass(kind)
    if cls is None:
        return None
    return getattr(cls, "history", {}).get(attribute)


def attributesFor(kind: str) -> Tuple[str, ...]:
    """Return the historic attributes registered for ``kind``."""
    cls = _lookupClass(kind)
    if cls is None:
        return ()
    return tuple(getattr(cls, "history", {}).keys())


def iterCatalog() -> Iterable[Tuple[str, str, HistorySpec]]:
    """Yield ``(kind, attribute, spec)`` for every registered class."""
    from arcline.graph.registry import iter_nodes, iter_edges
    for kind, cls in list(iter_nodes()) + list(iter_edges()):
        for attr, spec in getattr(cls, "history", {}).items():
            yield kind, attr, spec
