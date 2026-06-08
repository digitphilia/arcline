# -*- encoding: utf-8 -*-

"""
Plotly Figure Builder for the Network View
------------------------------------------

Assembles the :class:`plotly.graph_objects.Figure` rendered by the
``/dashboard/visualize`` page. Edges are drawn as a single
``Scattergl`` trace with ``None``-separated segments; nodes are
emitted as one ``Scattergl`` trace per ``kind`` so the legend
doubles as a kind picker. The geographic mode uses
``Scattermapbox`` traces over an OpenStreetMap tile background.

Arrow head annotations are suppressed automatically when the graph
has more than :data:`ARROW_THRESHOLD` edges to keep render time
predictable on dense networks.
"""

from typing import Any, Dict, List, Tuple

import plotly.graph_objects as go

from arcline.dashboard.viz.layouts import LayoutMode, computeLayout
from arcline.dashboard.viz.styles import kindColor
from arcline.graph.base.graph import AbstractGraph


ARROW_THRESHOLD : int = 2000
_EDGE_LINE_COLOR : str = "#888888"


def __hover_text__(payload : Dict[str, Any]) -> str:
    """
    Format a pydantic ``model_dump()`` payload into a multi-line
    Plotly hover string.

    :type  payload: Dict[str, Any]
    :param payload: The dictionary payload to format.

    :rtype:   str
    :returns: Multi-line ``"key: value"`` string.
    """

    return "<br>".join(
        f"<b>{key}</b>: {value}" for key, value in payload.items()
    )


def __build_edge_segments__(
        graph : AbstractGraph,
        positions : Dict[str, Tuple[float, float]]
) -> Tuple[List[float], List[float], List[str]]:
    """
    Interleave edge endpoints with ``None`` separators so a single
    ``Scattergl`` line trace can render the entire edge set.

    :type  graph: AbstractGraph
    :param graph: The live backend graph.

    :type  positions: Dict[str, Tuple[float, float]]
    :param positions: Node positions.

    :rtype:   Tuple[List[float], List[float], List[str]]
    :returns: Tuple of ``(xs, ys, hovers)`` ready for Plotly.
    """

    xs : List[float] = []
    ys : List[float] = []
    hovers : List[str] = []

    for edge in graph.edges:
        src = positions.get(edge.srcNode.hashKey)
        dst = positions.get(edge.dstNode.hashKey)
        if src is None or dst is None:
            continue

        xs.extend([src[0], dst[0], None])
        ys.extend([src[1], dst[1], None])
        hovers.extend([edge.hashKey, edge.hashKey, ""])

    return xs, ys, hovers


def __build_node_traces__(
        graph : AbstractGraph,
        positions : Dict[str, Tuple[float, float]],
        scatterCls : type
) -> List[Any]:
    """
    Emit one scatter trace per node ``kind`` so the legend exposes
    a per-kind toggle.

    :type  graph: AbstractGraph
    :param graph: The live backend graph.

    :type  positions: Dict[str, Tuple[float, float]]
    :param positions: Node positions.

    :type  scatterCls: type
    :param scatterCls: Either :class:`go.Scattergl` (abstract modes)
        or :class:`go.Scattermapbox` (geo mode).

    :rtype:   List[Any]
    :returns: List of Plotly trace instances.
    """

    byKind : Dict[str, List[Any]] = {}
    for node in graph.nodes:
        kind = type(node).kind
        byKind.setdefault(kind, []).append(node)

    traces : List[Any] = []
    isGeo = scatterCls is go.Scattermapbox

    for kind, nodes in byKind.items():
        xs : List[float] = []
        ys : List[float] = []
        labels : List[str] = []
        hovers : List[str] = []

        for node in nodes:
            pos = positions.get(node.hashKey, (0.0, 0.0))
            xs.append(pos[0])
            ys.append(pos[1])
            labels.append(node.name)
            hovers.append(__hover_text__(node.model_dump()))

        color = kindColor(kind, side = "node")

        if isGeo:
            traces.append(
                go.Scattermapbox(
                    lon = xs, lat = ys, mode = "markers",
                    name = kind, text = labels, hovertext = hovers,
                    hoverinfo = "text",
                    marker = dict(size = 12, color = color),
                )
            )
        else:
            traces.append(
                go.Scattergl(
                    x = xs, y = ys, mode = "markers+text",
                    name = kind, text = labels,
                    textposition = "top center",
                    hovertext = hovers, hoverinfo = "text",
                    marker = dict(size = 14, color = color),
                )
            )

    return traces


def __build_arrow_annotations__(
        graph : AbstractGraph,
        positions : Dict[str, Tuple[float, float]]
) -> List[Dict[str, Any]]:
    """
    Build arrow-head annotations pointing from each edge's source to
    its destination. Returns an empty list when the graph exceeds
    :data:`ARROW_THRESHOLD` edges.

    :type  graph: AbstractGraph
    :param graph: The live backend graph.

    :type  positions: Dict[str, Tuple[float, float]]
    :param positions: Node positions.

    :rtype:   List[Dict[str, Any]]
    :returns: Plotly annotation dictionaries.
    """

    if graph.numEdges > ARROW_THRESHOLD:
        return []

    annotations : List[Dict[str, Any]] = []
    for edge in graph.edges:
        src = positions.get(edge.srcNode.hashKey)
        dst = positions.get(edge.dstNode.hashKey)
        if src is None or dst is None:
            continue

        annotations.append(
            dict(
                x = dst[0], y = dst[1], ax = src[0], ay = src[1],
                xref = "x", yref = "y", axref = "x", ayref = "y",
                showarrow = True, arrowhead = 3,
                arrowsize = 1.1, arrowwidth = 1,
                arrowcolor = _EDGE_LINE_COLOR, opacity = 0.7,
            )
        )

    return annotations


def buildFigure(
        graph : AbstractGraph, mode : LayoutMode = "spring"
) -> go.Figure:
    """
    Build the full network figure for the visualize page.

    :type  graph: AbstractGraph
    :param graph: The live backend graph.

    :type  mode: LayoutMode
    :param mode: Layout mode (``"spring"``, ``"tiered"``, ``"geo"``).

    :rtype:   go.Figure
    :returns: A Plotly figure ready to be assigned to
        ``dcc.Graph.figure``.
    """

    positions = computeLayout(graph, mode = mode)
    xs, ys, hovers = __build_edge_segments__(graph, positions)

    if mode == "geo":
        edgeTrace = go.Scattermapbox(
            lon = xs, lat = ys, mode = "lines",
            line = dict(color = _EDGE_LINE_COLOR, width = 1),
            hoverinfo = "skip", showlegend = False,
        )
        nodeTraces = __build_node_traces__(
            graph, positions, scatterCls = go.Scattermapbox
        )
        layout = go.Layout(
            showlegend = True, hovermode = "closest",
            margin = dict(l = 0, r = 0, t = 10, b = 0), height = 720,
            mapbox = dict(
                style = "open-street-map", zoom = 2,
                center = dict(lat = 20, lon = 0),
            ),
        )
        return go.Figure(data = [edgeTrace, *nodeTraces], layout = layout)

    edgeTrace = go.Scattergl(
        x = xs, y = ys, mode = "lines",
        line = dict(color = _EDGE_LINE_COLOR, width = 1),
        hovertext = hovers, hoverinfo = "skip", showlegend = False,
    )
    nodeTraces = __build_node_traces__(
        graph, positions, scatterCls = go.Scattergl
    )

    layout = go.Layout(
        showlegend = True, hovermode = "closest",
        margin = dict(l = 0, r = 0, t = 10, b = 0), height = 720,
        xaxis = dict(showgrid = False, zeroline = False, visible = False),
        yaxis = dict(showgrid = False, zeroline = False, visible = False),
        annotations = __build_arrow_annotations__(graph, positions),
    )

    return go.Figure(data = [edgeTrace, *nodeTraces], layout = layout)
