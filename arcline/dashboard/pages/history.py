# -*- encoding: utf-8 -*-

"""
History Page (Phase 1.5 Placeholder)
------------------------------------

Phase 1 ships only a placeholder informational banner; the page
will be wired up to :mod:`arcline.historian` in Phase 1.5.
"""

import dash
import dash_bootstrap_components as dbc
from dash import html


dash.register_page(
    __name__, path = "/dashboard/history", name = "History",
    title = "arcline | History", order = 5,
)


def layout() -> html.Div:
    """
    Render the placeholder banner.

    :rtype:   html.Div
    :returns: An info alert announcing the future Phase 1.5 wiring.
    """

    return html.Div(
        dbc.Alert(
            "History - Coming in Phase 1.5", color = "info",
            className = "m-4",
        )
    )
