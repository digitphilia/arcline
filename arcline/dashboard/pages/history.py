# -*- encoding: utf-8 -*-

"""
History Page
------------

The ``/dashboard/history`` view drives the historian: pick an entity
(node or edge) from the bound project, choose one of its registered
historic attributes, and inspect the time-series, distribution, and
summary stats either from the warehouse (live) or from the local
Parquet cache (offline mode).

The actual fetch + rendering logic lives in
:mod:`arcline.dashboard.callbacks.history_cb` so this module stays
declarative.
"""

from datetime import date, timedelta

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html

from arcline.dashboard.state import session
from arcline.historian import iterCatalog


dash.register_page(
    __name__, path = "/dashboard/history", name = "History",
    title = "arcline | History", order = 5,
)


def _kindsWithHistory() -> list:
    seen = set()
    for kind, _attr, _spec in iterCatalog():
        seen.add(kind)
    return sorted(seen)


def _selectorCard() -> dbc.Card:
    today = date.today()
    twoYearsAgo = today - timedelta(days = 730)
    return dbc.Card(
        [
            dbc.CardHeader("Selection"),
            dbc.CardBody(
                [
                    dbc.Label("Entity type"),
                    dbc.RadioItems(
                        id = "history-entity-type",
                        options = [
                            {"label": "Nodes", "value": "node"},
                            {"label": "Edges", "value": "edge"},
                        ],
                        value = "edge",
                        inline = True,
                        className = "mb-3",
                    ),
                    dbc.Label("Entity"),
                    dcc.Dropdown(
                        id = "history-entity-dropdown",
                        placeholder = "Pick an entity",
                        searchable = True,
                        className = "mb-3",
                    ),
                    dbc.Label("Attribute"),
                    dcc.Dropdown(
                        id = "history-attribute-dropdown",
                        placeholder = "Pick an attribute",
                        className = "mb-3",
                    ),
                    dbc.Label("Date range"),
                    dcc.DatePickerRange(
                        id = "history-date-range",
                        start_date = twoYearsAgo.isoformat(),
                        end_date = today.isoformat(),
                        display_format = "YYYY-MM-DD",
                        className = "mb-3 d-block",
                    ),
                    dbc.Label("Aggregation"),
                    dbc.RadioItems(
                        id = "history-aggregation",
                        options = [
                            {"label": "Raw", "value": "raw"},
                            {"label": "Weekly", "value": "W"},
                            {"label": "Monthly", "value": "M"},
                        ],
                        value = "raw",
                        inline = True,
                        className = "mb-3",
                    ),
                    dbc.Button(
                        "Refresh from DB",
                        id = "history-refresh-btn",
                        color = "primary", size = "sm",
                    ),
                ],
            ),
        ],
        className = "m-2",
    )


def _chartsCard() -> dbc.Card:
    return dbc.Card(
        [
            dbc.CardHeader("Charts"),
            dbc.CardBody(
                [
                    html.Div(id = "history-summary", className = "mb-3"),
                    dcc.Graph(id = "history-timeseries"),
                    dcc.Graph(id = "history-distribution"),
                ],
            ),
        ],
        className = "m-2",
    )


def layout() -> html.Div:
    if not session.isBound():
        return html.Div(
            dbc.Alert(
                "No project bound. Launch the dashboard with a project path.",
                color = "info", className = "m-4",
            ),
        )

    if not _kindsWithHistory():
        return html.Div(
            dbc.Alert(
                "No HistorySpec definitions are registered for this project's "
                "node/edge classes. Add a `history` ClassVar to enable history.",
                color = "warning", className = "m-4",
            ),
        )

    return dbc.Row(
        [
            dbc.Col(_selectorCard(), md = 4),
            dbc.Col(_chartsCard(), md = 8),
        ],
        className = "g-0",
    )
