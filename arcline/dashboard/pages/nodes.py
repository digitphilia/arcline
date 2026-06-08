# -*- encoding: utf-8 -*-

"""
Nodes Page
----------

CRUD page for the project's node list. Shows the KPI strip and a
table of every node along with an "Add Node" button that opens a
modal containing a kind picker and the dynamically-rendered
:func:`makeNodeForm`.
"""

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html

from arcline.dashboard.components import makeKpiStrip, makeNodeTable
from arcline.dashboard.state import session
from arcline.graph.registry import iter_nodes


dash.register_page(
    __name__, path = "/dashboard/nodes", name = "Nodes",
    title = "arcline | Nodes", order = 1,
)


def __no_project_layout__() -> html.Div:
    """
    Placeholder layout when no project is bound.

    :rtype:   html.Div
    :returns: An info alert directing the user to bind a project.
    """

    return html.Div(
        dbc.Alert(
            "No project bound; nodes cannot be listed.",
            color = "warning", className = "m-4",
        )
    )


def __bound_layout__() -> html.Div:
    """
    Build the CRUD layout once a project is bound.

    :rtype:   html.Div
    :returns: Nodes page contents.
    """

    graph = session.getGraph()
    kindOptions = [
        {"label": kind, "value": kind} for kind, _ in iter_nodes()
    ]

    toolbar = dbc.Row(
        [
            dbc.Col(
                dbc.Button(
                    "Add Node", id = "add-node-btn", color = "primary"
                ),
                width = "auto",
            ),
            dbc.Col(
                dbc.Button(
                    "Delete Selected", id = "delete-node-btn",
                    color = "danger", outline = True,
                ),
                width = "auto",
            ),
        ],
        className = "g-2 my-2",
    )

    modal = dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Add / Edit Node")),
            dbc.ModalBody(
                [
                    dbc.Label("Kind"),
                    dcc.Dropdown(
                        id = "node-kind-select",
                        options = kindOptions,
                        value = kindOptions[0]["value"]
                        if kindOptions else None,
                        clearable = False, className = "mb-3",
                    ),
                    html.Div(id = "node-form-area"),
                ]
            ),
        ],
        id = "node-modal", is_open = False, size = "lg",
    )

    return html.Div(
        [
            makeKpiStrip(graph),
            toolbar,
            makeNodeTable(graph),
            modal,
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
