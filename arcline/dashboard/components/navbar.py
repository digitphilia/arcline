# -*- encoding: utf-8 -*-

"""
Top Navigation Bar Component
----------------------------

Builds the dashboard's persistent top :class:`dbc.NavbarSimple` with
the project brand on the left and one navigation link per top-level
page on the right.
"""

import dash_bootstrap_components as dbc


_NAV_LINKS : list = [
    ("Home", "/"),
    ("Nodes", "/dashboard/nodes"),
    ("Edges", "/dashboard/edges"),
    ("Visualize", "/dashboard/visualize"),
    ("History", "/dashboard/history"),
    ("Solve", "/dashboard/solve"),
    ("Scenarios", "/dashboard/scenarios"),
]


def make_navbar(project_name : str = "(no project)") -> dbc.NavbarSimple:
    """
    Construct the dashboard top navigation bar.

    The brand on the left reads ``"arcline | <project_name>"``;
    each entry in :data:`_NAV_LINKS` is rendered as a
    :class:`dbc.NavLink` on the right.

    :type  project_name: str
    :param project_name: The project name to surface alongside the
        ``"arcline"`` brand label.

    :rtype:   dbc.NavbarSimple
    :returns: A configured navbar component.
    """

    links = [
        dbc.NavLink(label, href = href, active = "exact")
        for label, href in _NAV_LINKS
    ]

    return dbc.NavbarSimple(
        children = links,
        brand = f"arcline | {project_name}",
        brand_href = "/",
        color = "primary",
        dark = True,
        fluid = True,
        sticky = "top",
    )
