# -*- encoding: utf-8 -*-

"""
Home Page
---------

Landing page for the dashboard. When a project is bound, surfaces
the manifest metadata (name, description, schema version, node and
edge counts) inside a summary card. When no project is bound,
renders a friendly hint guiding the user toward the CLI entry point.
"""

import dash
import dash_bootstrap_components as dbc
from dash import html

from arcline.dashboard.state import session


dash.register_page(
    __name__, path = "/", name = "Home", title = "arcline | Home",
    order = 0,
)


def __no_project_layout__() -> html.Div:
    """
    Build the placeholder layout when no project has been bound.

    :rtype:   html.Div
    :returns: A friendly information panel.
    """

    return html.Div(
        [
            dbc.Alert(
                [
                    html.H4(
                        "No project bound", className = "alert-heading"
                    ),
                    html.P(
                        "Launch the dashboard with a project path "
                        "to start exploring the network:"
                    ),
                    html.Pre(
                        "arcline dashboard ./my_network",
                        className = "mb-0",
                    ),
                ],
                color = "info", className = "m-4",
            ),
        ]
    )


def __project_layout__() -> html.Div:
    """
    Build the home layout for a bound project.

    :rtype:   html.Div
    :returns: A card summarising project metadata.
    """

    project = session.get_project()
    graph = session.get_graph()

    rows = [
        ("Name", project.name),
        ("Description", project.description or "(none)"),
        ("Schema version", project.schemaVersion),
        ("Created at", project.createdAt),
        ("Updated at", project.updatedAt or "(unsaved)"),
        ("Path", str(project.path)),
        ("Nodes", graph.numNodes),
        ("Edges", graph.numEdges),
    ]

    body = dbc.Table(
        [
            html.Tbody(
                [
                    html.Tr(
                        [
                            html.Th(label, scope = "row"),
                            html.Td(str(value)),
                        ]
                    )
                    for label, value in rows
                ]
            )
        ],
        bordered = True, hover = True, striped = True, size = "sm",
    )

    card = dbc.Card(
        [
            dbc.CardHeader(html.H4("Project Summary", className = "mb-0")),
            dbc.CardBody(body),
        ],
        className = "m-4",
    )

    return html.Div([card])


def layout() -> html.Div:
    """
    Top-level page layout function (Dash re-invokes this on every
    navigation, so it always reflects the current session state).

    :rtype:   html.Div
    :returns: The page contents.
    """

    if not session.is_bound():
        return __no_project_layout__()

    return __project_layout__()
