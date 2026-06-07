# -*- encoding: utf-8 -*-

"""
Solve Page (Phase 2 Placeholder)
--------------------------------

Phase 1 ships only a placeholder informational banner; the page
will be wired up to :mod:`arcline.optim` in Phase 2.
"""

import dash
import dash_bootstrap_components as dbc
from dash import html


dash.register_page(
    __name__, path = "/dashboard/solve", name = "Solve",
    title = "arcline | Solve", order = 4,
)


def layout() -> html.Div:
    """
    Render the placeholder banner.

    :rtype:   html.Div
    :returns: An info alert announcing the future Phase 2 wiring.
    """

    return html.Div(
        dbc.Alert(
            "Solve - Coming in Phase 2", color = "info",
            className = "m-4",
        )
    )
