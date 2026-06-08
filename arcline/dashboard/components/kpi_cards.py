# -*- encoding: utf-8 -*-

"""
KPI Summary Cards Component
---------------------------

Builds a horizontal strip of summary cards (total node count, edge
count, aggregate capacity, per-kind node counts) intended to sit at
the top of the Nodes / Edges / Visualize pages and give the analyst
an at-a-glance view of the network size.
"""

from typing import Any, Dict, List

import dash_bootstrap_components as dbc
from dash import html

from arcline.graph.base.graph import AbstractGraph
from arcline.graph.registry import iter_nodes


_CAPACITY_FIELDS : List[str] = ["maxCapacity"]


def __make_card__(title : str, value : Any) -> dbc.Col:
    """
    Build a single KPI card.

    :type  title: str
    :param title: Card title shown as a small caption.

    :type  value: Any
    :param value: Headline metric value rendered as the card body.

    :rtype:   dbc.Col
    :returns: A column-wrapped :class:`dbc.Card` instance.
    """

    card = dbc.Card(
        dbc.CardBody(
            [
                html.H4(str(value), className = "mb-0"),
                html.P(title, className = "text-muted small mb-0"),
            ]
        ),
        className = "kpi-card shadow-sm",
    )
    return dbc.Col(card, width = "auto", className = "mb-2")


def __aggregate_capacity__(graph : AbstractGraph) -> float:
    """
    Sum the ``maxCapacity`` attribute across every node that exposes
    it; finite values only (skips ``inf`` defaults).

    :type  graph: AbstractGraph
    :param graph: The live backend graph.

    :rtype:   float
    :returns: Aggregate finite capacity across the network.
    """

    total : float = 0.0
    for node in graph.nodes:
        payload : Dict[str, Any] = node.model_dump()
        for field in _CAPACITY_FIELDS:
            value = payload.get(field)
            if isinstance(value, (int, float)) \
                    and value not in (float("inf"), float("-inf")):
                total += float(value)

    return total


def __kind_counts__(graph : AbstractGraph) -> Dict[str, int]:
    """
    Count how many nodes are present for each registered ``kind``.

    :type  graph: AbstractGraph
    :param graph: The live backend graph.

    :rtype:   Dict[str, int]
    :returns: Mapping of ``kind`` to occurrence count.
    """

    counts : Dict[str, int] = {kind: 0 for kind, _ in iter_nodes()}
    for node in graph.nodes:
        kind = type(node).kind
        counts[kind] = counts.get(kind, 0) + 1

    return counts


def makeKpiStrip(graph : AbstractGraph) -> dbc.Row:
    """
    Build the KPI strip row.

    :type  graph: AbstractGraph
    :param graph: The live backend graph.

    :rtype:   dbc.Row
    :returns: A :class:`dbc.Row` of KPI cards.
    """

    cards : List[dbc.Col] = [
        __make_card__("Nodes", graph.numNodes),
        __make_card__("Edges", graph.numEdges),
        __make_card__(
            "Total Capacity", f"{__aggregate_capacity__(graph):,.0f}"
        ),
    ]

    for kind, count in __kind_counts__(graph).items():
        cards.append(__make_card__(f"{kind} count", count))

    return dbc.Row(cards, className = "g-2 my-2")
