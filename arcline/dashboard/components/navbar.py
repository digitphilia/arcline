# -*- encoding: utf-8 -*-

"""
Top Navigation Bar Component
----------------------------

Builds the dashboard's persistent top :class:`dbc.NavbarSimple` with
the project brand on the left and one navigation link per top-level
page on the right.
"""

import dash_bootstrap_components as dbc
from dash import html

from arcline.historian.connection import getDsn, testConnection


_NAV_LINKS : list = [
    ("Home", "/"),
    ("Nodes", "/dashboard/nodes"),
    ("Edges", "/dashboard/edges"),
    ("Visualize", "/dashboard/visualize"),
    ("History", "/dashboard/history"),
    ("Solve", "/dashboard/solve"),
    ("Scenarios", "/dashboard/scenarios"),
]


def _dbStatusPill() -> dbc.Badge:
    """
    Render the historian DB status pill.

    Three states surfaced to the operator:
      * green  - DSN set and SELECT 1 succeeded -> live mode
      * amber  - DSN set but unreachable        -> cached-only fallback
      * red    - DSN unset                      -> historian offline
    """
    dsn = getDsn()
    if dsn is None:
        color, label = "danger", "DB: offline"
    elif testConnection():
        color, label = "success", "DB: live"
    else:
        color, label = "warning", "DB: cached-only"
    return dbc.Badge(
        label, color = color, pill = True,
        className = "ms-2", id = "db-status-pill",
    )


def makeNavbar(projectName : str = "(no project)") -> dbc.NavbarSimple:
    """
    Construct the dashboard top navigation bar.

    The brand on the left reads ``"arcline | <projectName>"``;
    each entry in :data:`_NAV_LINKS` is rendered as a
    :class:`dbc.NavLink` on the right.

    :type  projectName: str
    :param projectName: The project name to surface alongside the
        ``"arcline"`` brand label.

    :rtype:   dbc.NavbarSimple
    :returns: A configured navbar component.
    """

    links = [
        dbc.NavLink(label, href = href, active = "exact")
        for label, href in _NAV_LINKS
    ]
    links.append(_dbStatusPill())

    return dbc.NavbarSimple(
        children = links,
        brand = f"arcline | {projectName}",
        brandHref = "/",
        color = "primary",
        dark = True,
        fluid = True,
        sticky = "top",
    )
