# -*- encoding: utf-8 -*-

"""
Edges Page
----------

CRUD page for the project's edge list. Mirrors the structure of the
nodes page: KPI strip, table of every edge, and an "Add Edge" button
that opens a modal containing a kind picker and the dynamically
rendered :func:`make_edge_form`.
"""

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html

from arcline.dashboard.components import make_edge_table, make_kpi_strip
from arcline.dashboard.state import session
from arcline.graph.registry import iter_edges


dash.register_page(
    __name__, path = "/dashboard/edges", name = "Edges",
    title = "arcline | Edges", order = 2,
)


def __no_project_layout__() -> html.Div:
    """
    Placeholder layout when no project is bound.

    :rtype:   html.Div
    :returns: An info alert directing the user to bind a project.
    """

    return html.Div(
        dbc.Alert(
            "No project bound; edges cannot be listed.",
            color = "warning", className = "m-4",
        )
    )


def __bound_layout__() -> html.Div:
    """
    Build the CRUD layout once a project is bound.

    :rtype:   html.Div
    :returns: Edges page contents.
    """

    graph = session.get_graph()
    kind_options = [
        {"label": kind, "value": kind} for kind, _ in iter_edges()
    ]

    toolbar = dbc.Row(
        [
            dbc.Col(
                dbc.Button(
                    "Add Edge", id = "add-edge-btn", color = "primary"
                ),
                width = "auto",
            ),
            dbc.Col(
                dbc.Button(
                    "Delete Selected", id = "delete-edge-btn",
                    color = "danger", outline = True,
                ),
                width = "auto",
            ),
        ],
        className = "g-2 my-2",
    )

    modal = dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Add / Edit Edge")),
            dbc.ModalBody(
                [
                    dbc.Label("Kind"),
                    dcc.Dropdown(
                        id = "edge-kind-select",
                        options = kind_options,
                        value = kind_options[0]["value"]
                        if kind_options else None,
                        clearable = False, className = "mb-3",
                    ),
                    html.Div(id = "edge-form-area"),
                ]
            ),
        ],
        id = "edge-modal", is_open = False, size = "lg",
    )

    return html.Div(
        [
            make_kpi_strip(graph),
            toolbar,
            make_edge_table(graph),
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

    if not session.is_bound():
        return __no_project_layout__()

    return __bound_layout__()
