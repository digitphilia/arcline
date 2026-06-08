# -*- encoding: utf-8 -*-

"""
Network Visualization Helpers
=============================

Layout computation, style resolution, and Plotly figure building for
the dashboard's ``/dashboard/visualize`` page. Two abstract layouts
(spring, tiered) and one geographic layout (lat/lon scatter on an
OpenStreetMap tile background) are supported.
"""

from arcline.dashboard.viz.layouts import LayoutMode, computeLayout
from arcline.dashboard.viz.plotly_graph import buildFigure
from arcline.dashboard.viz.styles import kindColor, kindIcon

__all__ = [
    "LayoutMode",
    "computeLayout",
    "buildFigure",
    "kindColor",
    "kindIcon",
]
