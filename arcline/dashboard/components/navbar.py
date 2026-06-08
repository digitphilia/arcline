# -*- encoding: utf-8 -*-

"""
Top Navigation Bar Component
----------------------------

Glassmorphism navbar with the project brand on the left, page nav
in the middle, and a control cluster on the right (DB-status pill,
theme toggle, global Save button).
"""

import time

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


_DB_STATUS_TTL_S : float = 30.0
_dbStatusCache : dict = {"expiresAt": 0.0, "color": "danger", "label": "DB offline"}


def _resolveDbStatus(now: float) -> tuple:
    """
    Compute the (color, label) pair for the DB pill, with a TTL cache.

    Without the cache, ``testConnection()`` would issue a synchronous
    ``SELECT 1`` on every page navigation; over a 5-second timeout
    that makes navbar render dominate the request latency.
    """
    if now < _dbStatusCache["expiresAt"]:
        return _dbStatusCache["color"], _dbStatusCache["label"]
    dsn = getDsn()
    if dsn is None:
        color, label = "danger", "DB offline"
    elif testConnection():
        color, label = "success", "DB live"
    else:
        color, label = "warning", "DB cached-only"
    _dbStatusCache["color"] = color
    _dbStatusCache["label"] = label
    _dbStatusCache["expiresAt"] = now + _DB_STATUS_TTL_S
    return color, label


def _dbStatusPill() -> dbc.Badge:
    """
    Render the historian DB status pill (green / amber / red).
    """
    color, label = _resolveDbStatus(time.monotonic())
    return dbc.Badge(
        label, color = color, pill = True,
        className = "ms-2", id = "db-status-pill",
    )


def _themeToggle() -> html.Button:
    """
    Theme toggle button wired to the clientside ``arcToggleTheme``
    helper exposed by ``assets/theme.js``.
    """
    return html.Button(
        "\u25D0", id = "arc-theme-toggle-btn",
        title = "Toggle theme",
        className = "arc-theme-toggle ms-2",
        n_clicks = 0,
        **{"data-arc-action": "toggle-theme"},
    )


def _saveButton() -> dbc.Button:
    """
    Global "Save project" button (wired by visualize callbacks).
    """
    return dbc.Button(
        "Save", id = "arc-global-save-btn", color = "primary",
        outline = True, size = "sm", className = "ms-2",
        n_clicks = 0,
    )


def makeNavbar(projectName : str = "(no project)") -> dbc.Navbar:
    """
    Construct the dashboard top navigation bar.

    :type  projectName: str
    :param projectName: Project name surfaced alongside the brand.

    :rtype:   dbc.Navbar
    :returns: A configured navbar component.
    """

    navLinks = dbc.Nav(
        [
            dbc.NavLink(label, href = href, active = "exact")
            for label, href in _NAV_LINKS
        ],
        navbar = True, className = "ms-auto me-3",
    )

    rightCluster = html.Div(
        [
            _dbStatusPill(),
            _themeToggle(),
            _saveButton(),
            html.Div(id = "arc-global-save-toast"),
        ],
        className = "d-flex align-items-center",
    )

    brand = dbc.NavbarBrand(
        f"arcline | {projectName}", href = "/",
    )

    return dbc.Navbar(
        dbc.Container(
            [brand, navLinks, rightCluster],
            fluid = True, className = "align-items-center",
        ),
        sticky = "top",
        className = "arc-navbar",
        color = None,
    )
