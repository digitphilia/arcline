# -*- encoding: utf-8 -*-

"""
Visual Style Resolution
-----------------------

Resolves the display colour and (optionally) icon path for a graph
``kind`` by instantiating the registered class with placeholder
required arguments and reading its ``nodeColor`` / ``edgeColor`` /
``imagePath`` properties.

Resolutions are memoised with :func:`functools.lru_cache` so the
relatively expensive pydantic instantiation only runs once per kind.
"""

import functools
from typing import Literal, Optional

from arcline.graph.registry import resolve_edge, resolve_node


_DEFAULT_COLOR : str = "#999999"


def __probe_node__(kind : str):
    """
    Instantiate the node class registered under ``kind`` with the
    minimum required arguments so its ``nodeColor`` / ``imagePath``
    properties can be read.

    :type  kind: str
    :param kind: Registered node ``kind``.

    :rtype:   Optional[AbstractNode]
    :returns: A throwaway probe instance, or ``None`` if construction
        fails because required fields cannot be defaulted.
    """

    try:
        cls = resolve_node(kind)
        return cls(name = "_probe", hashKey = "_probe")
    except Exception:
        return None


def __probe_edge__(kind : str):
    """
    Instantiate the edge class registered under ``kind`` with the
    minimum required arguments (including two throwaway node
    references) so its ``edgeColor`` property can be read.

    :type  kind: str
    :param kind: Registered edge ``kind``.

    :rtype:   Optional[AbstractEdge]
    :returns: A throwaway probe instance, or ``None`` if construction
        fails because required fields cannot be defaulted.
    """

    try:
        from arcline.graph.library.supplier import SupplierNode

        cls = resolve_edge(kind)
        probeSrc = SupplierNode(
            name = "_probe-src", hashKey = "_probe-src"
        )
        probeDst = SupplierNode(
            name = "_probe-dst", hashKey = "_probe-dst"
        )
        return cls(
            name = "_probe", hashKey = "_probe",
            srcNode = probeSrc, dstNode = probeDst,
        )
    except Exception:
        return None


@functools.lru_cache(maxsize = 64)
def kindColor(
        kind : str, side : Literal["node", "edge"] = "node"
) -> str:
    """
    Resolve the display colour for ``kind`` by probing the registered
    class. Falls back to a neutral grey when probing fails.

    :type  kind: str
    :param kind: Registered ``kind`` discriminator.

    :type  side: Literal["node", "edge"]
    :param side: Whether ``kind`` belongs to the node or edge
        registry.

    :rtype:   str
    :returns: A HEX colour string ready for Plotly markers / lines.
    """

    probe = (
        __probe_node__(kind) if side == "node" else __probe_edge__(kind)
    )
    if probe is None:
        return _DEFAULT_COLOR

    if side == "node":
        color = getattr(probe, "nodeColor", None)
    else:
        color = getattr(probe, "edgeColor", None)

    return color or _DEFAULT_COLOR


@functools.lru_cache(maxsize = 64)
def kindIcon(kind : str) -> Optional[str]:
    """
    Resolve the icon path for a node ``kind`` by probing the
    registered class.

    :type  kind: str
    :param kind: Registered node ``kind``.

    :rtype:   Optional[str]
    :returns: Icon path (or ``None`` when the class declares none).
    """

    probe = __probe_node__(kind)
    if probe is None:
        return None

    return getattr(probe, "imagePath", None)
