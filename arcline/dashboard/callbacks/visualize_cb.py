# -*- encoding: utf-8 -*-

"""
Visualize Page Callbacks
------------------------

Re-renders the network figure whenever the user toggles the layout
mode or the graph becomes dirty, and surfaces the attributes of the
most recently clicked entity in the side panel.
"""

from typing import Any, Dict, List, Optional

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, html, no_update

from arcline.dashboard.state import session
from arcline.dashboard.state.store import STORE_GRAPH_DIRTY
from arcline.dashboard.viz import build_figure


def __point_to_payload__(
        point : Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Pull a renderable payload out of a Plotly ``clickData`` point.

    :type  point: Dict[str, Any]
    :param point: One entry of ``clickData["points"]``.

    :rtype:   Optional[Dict[str, Any]]
    :returns: A flat dict to render in the side panel, or ``None``
        when nothing useful was selected.
    """

    text = point.get("text") or point.get("hovertext")
    if not text:
        return None

    if not session.is_bound():
        return None

    graph = session.get_graph()
    for node in graph.nodes:
        if node.name == text or node.hashKey == text:
            return {"type": type(node).kind, **node.model_dump()}

    return {"raw": text}


def __payload_to_rows__(payload : Dict[str, Any]) -> List[Any]:
    """
    Render a payload mapping as a table-like list of paragraphs.

    :type  payload: Dict[str, Any]
    :param payload: Flat attribute mapping.

    :rtype:   List[Any]
    :returns: A list of Dash components for the side panel.
    """

    rows = []
    for key, value in payload.items():
        rows.append(
            html.P(
                [html.Strong(f"{key}: "), html.Span(str(value))],
                className = "mb-1 small",
            )
        )
    return rows


def register(app : Dash) -> None:
    """
    Attach all visualize-page callbacks to ``app``.

    :type  app: Dash
    :param app: The Dash instance to register against.

    :rtype:   None
    """

    @app.callback(
        Output("viz-graph", "figure"),
        Input("viz-mode", "value"),
        Input(STORE_GRAPH_DIRTY, "data"),
        prevent_initial_call = False,
    )
    def refresh_figure(mode : Optional[str], dirty : Any) -> Any:
        """
        Rebuild the network figure when either the layout mode or
        the graph-dirty tick changes.
        """

        if not session.is_bound():
            return no_update

        return build_figure(session.get_graph(), mode = mode or "spring")

    @app.callback(
        Output("viz-selected-panel", "children"),
        Input("viz-graph", "clickData"),
        prevent_initial_call = True,
    )
    def show_selected(click_data : Optional[Dict[str, Any]]) -> Any:
        """
        Surface attributes of the clicked entity in the side panel.
        """

        if not click_data:
            return no_update

        points = click_data.get("points") or []
        if not points:
            return no_update

        payload = __point_to_payload__(points[0])
        if payload is None:
            return dbc.Alert(
                "No metadata available for selection.",
                color = "secondary", className = "small mb-0",
            )

        return html.Div(__payload_to_rows__(payload))
