# -*- encoding: utf-8 -*-

"""
Visualize Page
--------------

Modern D3-powered network canvas with full canvas CRUD:

  * Click           -> selection (mirrors into side drawer)
  * Double-click    -> open edit form for the entity
  * Right-click     -> context menu (edit / delete / duplicate /
                       view history deep-link)
  * Drag (default)  -> reposition node
  * Drag (Connect mode toggled on) -> draw a transient edge that
    resolves on drop and opens the edge create form prefilled with
    src / dst
  * + Node FAB      -> kind picker, then create form
"""

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html

from arcline.dashboard.components import makeKpiStrip
from arcline.dashboard.d3 import NetworkCanvas
from arcline.dashboard.state import session
from arcline.dashboard.theme import canvasTheme, serializeGraph
from arcline.graph.registry import iter_edges, iter_nodes


dash.register_page(
    __name__, path = "/dashboard/visualize", name = "Visualize",
    title = "arcline | Visualize", order = 3,
)


def __noProjectLayout__() -> html.Div:
    """
    Placeholder layout when no project is bound.
    """
    return html.Div(
        dbc.Alert(
            "No project bound; nothing to visualise.",
            color = "warning", className = "m-4",
        )
    )


def __layoutModeControl__() -> dbc.Card:
    """
    Segmented control for layout mode (force / tiered / geo).
    """
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(
                    "Layout",
                    className = "text-muted small mb-2",
                    style = {"letterSpacing": "0.05em"},
                ),
                dbc.RadioItems(
                    id = "viz-mode",
                    options = [
                        {"label": "Force",  "value": "force"},
                        {"label": "Tiered", "value": "tiered"},
                        {"label": "Geo",    "value": "geo"},
                    ],
                    value = "force", inline = True,
                    className = "arc-segmented",
                    inputClassName = "btn-check",
                    labelClassName = "btn btn-outline-primary btn-sm",
                ),
            ]
        ),
        className = "mb-2 glass-card arc-fade-in",
    )


def __sideDrawer__() -> html.Div:
    """
    Right-side glass drawer that shows the currently-selected entity
    and exposes an in-place edit form.
    """
    return html.Div(
        [
            html.H6("Selection", className = "mb-2"),
            html.Div(
                "Click a node or edge to inspect, double-click to edit.",
                id = "viz-selected-panel",
                className = "text-muted small",
            ),
            html.Hr(),
            html.H6("Editor", className = "mb-2"),
            html.Div(
                id = "viz-editor-area",
                className = "small",
                children = html.Div(
                    "Double-click an entity to edit it here.",
                    className = "text-muted",
                ),
            ),
        ],
        className = "arc-side-drawer arc-fade-in",
    )


def __floatingActionBar__() -> html.Div:
    """
    Floating bottom bar inside the canvas: add node, toggle connect
    mode, save.
    """
    nodeKinds = sorted(k for k, _ in iter_nodes())
    edgeKinds = sorted(k for k, _ in iter_edges())

    return html.Div(
        [
            dcc.Store(id = "viz-connect-mode", data = False),
            dbc.DropdownMenu(
                label = "+ Node", color = "primary", size = "sm",
                children = [
                    dbc.DropdownMenuItem(
                        k.capitalize(),
                        id = {"type": "viz-add-node", "kind": k},
                        n_clicks = 0,
                    )
                    for k in nodeKinds
                ] or [dbc.DropdownMenuItem("(no node kinds)", disabled = True)],
            ),
            dbc.Button(
                "Connect",
                id = "viz-connect-toggle",
                color = "secondary", outline = True, size = "sm",
                n_clicks = 0,
            ),
            dbc.DropdownMenu(
                label = "+ Edge", color = "secondary", size = "sm",
                children = [
                    dbc.DropdownMenuItem(
                        k.capitalize(),
                        id = {"type": "viz-add-edge", "kind": k},
                        n_clicks = 0,
                    )
                    for k in edgeKinds
                ] or [dbc.DropdownMenuItem("(no edge kinds)", disabled = True)],
            ),
            dbc.Button(
                "Save",
                id = "viz-save-btn",
                color = "success", size = "sm",
                n_clicks = 0,
            ),
        ],
        className = "arc-fab",
    )


def __canvasWrapper__() -> html.Div:
    """
    Canvas + overlaid floating action bar.
    """
    graph = session.getGraph()
    serialized = serializeGraph(graph)
    theme = canvasTheme("dark")

    canvas = NetworkCanvas(
        id = "viz-canvas",
        nodes = serialized["nodes"],
        edges = serialized["edges"],
        theme = theme,
        iconBase = "/assets/icons/",
        layoutMode = "force",
        connectMode = False,
        ts = 0,
    )

    return html.Div(
        [canvas, __floatingActionBar__()],
        style = {"position": "relative"},
        className = "arc-fade-in",
    )


def __boundLayout__() -> html.Div:
    """
    Build the visualize layout once a project is bound.
    """
    graph = session.getGraph()

    return html.Div(
        [
            makeKpiStrip(graph),
            __layoutModeControl__(),
            dbc.Row(
                [
                    dbc.Col(__canvasWrapper__(), width = 9),
                    dbc.Col(__sideDrawer__(), width = 3),
                ],
                className = "g-3",
            ),
            # modal used for create / edit forms
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle(id = "viz-modal-title")),
                    dbc.ModalBody(id = "viz-modal-body"),
                ],
                id = "viz-modal", is_open = False, size = "lg",
            ),
            # toast for save / validation feedback
            dbc.Toast(
                id = "viz-toast", is_open = False, dismissable = True,
                duration = 3500, icon = "primary",
                style = {
                    "position": "fixed", "bottom": "24px", "right": "24px",
                    "minWidth": "280px", "zIndex": 9999,
                },
            ),
        ],
        className = "p-3",
    )


def layout() -> html.Div:
    """
    Top-level page layout function.
    """
    if not session.isBound():
        return __noProjectLayout__()
    return __boundLayout__()
