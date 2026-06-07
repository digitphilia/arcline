# -*- encoding: utf-8 -*-

"""
Network Layout Computation
--------------------------

Computes ``hashKey -> (x, y)`` position dictionaries for the three
supported visualization modes:

  * ``"spring"`` - force-directed layout via
    :func:`networkx.spring_layout`.
  * ``"tiered"`` - multipartite layout grouped by node ``kind``
    (supplier -> plant -> warehouse -> customer -> others).
  * ``"geo"``    - direct ``(longitude, latitude)`` mapping for any
    node carrying coordinates, falling back to ``(0, 0)`` otherwise.
"""

from typing import Dict, Literal, Tuple

import networkx

from arcline.graph.base.graph import AbstractGraph


LayoutMode = Literal["spring", "tiered", "geo"]


_TIER_BY_KIND : Dict[str, int] = {
    "supplier": 0,
    "plant": 1,
    "warehouse": 2,
    "customer": 3,
}
_DEFAULT_TIER : int = 4


def __spring_layout__(
        graph : AbstractGraph
) -> Dict[str, Tuple[float, float]]:
    """
    Compute a deterministic force-directed layout using a fixed seed.

    :type  graph: AbstractGraph
    :param graph: The live backend graph.

    :rtype:   Dict[str, Tuple[float, float]]
    :returns: ``hashKey -> (x, y)`` coordinate mapping.
    """

    positions = networkx.spring_layout(graph.G, seed = 42)
    return {
        str(key): (float(pos[0]), float(pos[1]))
        for key, pos in positions.items()
    }


def __tiered_layout__(
        graph : AbstractGraph
) -> Dict[str, Tuple[float, float]]:
    """
    Compute a multipartite layout with one column per node ``kind``.

    A copy of the underlying NetworkX graph is taken so the temporary
    ``subset`` attribute used by :func:`networkx.multipartite_layout`
    does not leak into the source graph.

    :type  graph: AbstractGraph
    :param graph: The live backend graph.

    :rtype:   Dict[str, Tuple[float, float]]
    :returns: ``hashKey -> (x, y)`` coordinate mapping.
    """

    kind_by_key = {node.hashKey: type(node).kind for node in graph.nodes}
    sub_graph = graph.G.copy()
    for hash_key in sub_graph.nodes:
        kind = kind_by_key.get(hash_key, "")
        sub_graph.nodes[hash_key]["subset"] = _TIER_BY_KIND.get(
            kind, _DEFAULT_TIER
        )

    positions = networkx.multipartite_layout(
        sub_graph, subset_key = "subset"
    )
    return {
        str(key): (float(pos[0]), float(pos[1]))
        for key, pos in positions.items()
    }


def __geo_layout__(
        graph : AbstractGraph
) -> Dict[str, Tuple[float, float]]:
    """
    Compute a geographic layout from ``latitude`` / ``longitude``.

    Nodes lacking coordinates are placed at the origin so they remain
    selectable in the figure even when geo data is incomplete.

    :type  graph: AbstractGraph
    :param graph: The live backend graph.

    :rtype:   Dict[str, Tuple[float, float]]
    :returns: ``hashKey -> (longitude, latitude)`` coordinate mapping.
    """

    positions : Dict[str, Tuple[float, float]] = {}
    for node in graph.nodes:
        lon = node.longitude if node.longitude is not None else 0.0
        lat = node.latitude if node.latitude is not None else 0.0
        positions[node.hashKey] = (float(lon), float(lat))

    return positions


def compute_layout(
        graph : AbstractGraph, mode : LayoutMode = "spring"
) -> Dict[str, Tuple[float, float]]:
    """
    Dispatch on ``mode`` to compute a ``hashKey -> (x, y)`` layout.

    :type  graph: AbstractGraph
    :param graph: The live backend graph.

    :type  mode: LayoutMode
    :param mode: One of ``"spring"``, ``"tiered"``, ``"geo"``.

    :raises ValueError: If ``mode`` is unknown.

    :rtype:   Dict[str, Tuple[float, float]]
    :returns: Layout coordinate mapping.
    """

    if mode == "spring":
        return __spring_layout__(graph)
    if mode == "tiered":
        return __tiered_layout__(graph)
    if mode == "geo":
        return __geo_layout__(graph)

    raise ValueError(f"Unknown layout mode {mode!r}.")
