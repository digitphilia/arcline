# -*- encoding: utf-8 -*-

"""
Scenarios Page (Phase 3 Placeholder)
------------------------------------

Phase 1 ships only a placeholder informational banner; the page
will be wired up to :mod:`arcline.scenarios` in Phase 3.
"""

import dash
import dash_bootstrap_components as dbc
from dash import html


dash.register_page(
    __name__, path = "/dashboard/scenarios", name = "Scenarios",
    title = "arcline | Scenarios", order = 6,
)


def layout() -> html.Div:
    """
    Render the placeholder banner.

    :rtype:   html.Div
    :returns: An info alert announcing the future Phase 3 wiring.
    """

    return html.Div(
        dbc.Alert(
            "Scenarios - Coming in Phase 3", color = "info",
            className = "m-4",
        )
    )
