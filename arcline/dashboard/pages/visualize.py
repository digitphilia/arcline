# -*- encoding: utf-8 -*-

"""
Visualize Page
--------------

Full-network visualisation built on top of
:func:`arcline.dashboard.viz.buildFigure`. A radio group at the top
of the page toggles between the three supported layout modes; a side
panel mirrors the attributes of the most recently clicked node or
edge.
"""

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html

from arcline.dashboard.components import makeKpiStrip
from arcline.dashboard.state import session
from arcline.dashboard.viz import buildFigure


dash.register_page(
    __name__, path = "/dashboard/visualize", name = "Visualize",
    title = "arcline | Visualize", order = 3,
)


def __no_project_layout__() -> html.Div:
    """
    Placeholder layout when no project is bound.

    :rtype:   html.Div
    :returns: A warning alert.
    """

    return html.Div(
        dbc.Alert(
            "No project bound; nothing to visualise.",
            color = "warning", className = "m-4",
        )
    )


def __bound_layout__() -> html.Div:
    """
    Build the visualize layout once a project is bound.

    :rtype:   html.Div
    :returns: The page contents.
    """

    graph = session.getGraph()
    figure = buildFigure(graph, mode = "spring")

    controls = dbc.Card(
        dbc.CardBody(
            dbc.RadioItems(
                id = "viz-mode",
                options = [
                    {"label": "Spring", "value": "spring"},
                    {"label": "Tiered", "value": "tiered"},
                    {"label": "Geo", "value": "geo"},
                ],
                value = "spring", inline = True,
            )
        ),
        className = "mb-2",
    )

    sidePanel = dbc.Card(
        [
            dbc.CardHeader(html.H6("Selection", className = "mb-0")),
            dbc.CardBody(
                html.Div(
                    "Click a node or edge to view its attributes.",
                    id = "viz-selected-panel",
                )
            ),
        ],
        className = "h-100",
    )

    return html.Div(
        [
            makeKpiStrip(graph),
            controls,
            dbc.Row(
                [
                    dbc.Col(
                        dcc.Graph(
                            id = "viz-graph", figure = figure,
                            config = {"displaylogo": False},
                        ),
                        width = 9,
                    ),
                    dbc.Col(sidePanel, width = 3),
                ],
                className = "g-2",
            ),
        ],
        className = "p-3",
    )


def layout() -> html.Div:
    """
    Top-level page layout function.

    :rtype:   html.Div
    :returns: The page contents.
    """

    if not session.isBound():
        return __no_project_layout__()

    return __bound_layout__()
