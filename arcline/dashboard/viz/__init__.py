# -*- encoding: utf-8 -*-

"""
Network Visualization Helpers
=============================

Layout computation, style resolution, and Plotly figure building for
the dashboard's ``/dashboard/visualize`` page. Two abstract layouts
(spring, tiered) and one geographic layout (lat/lon scatter on an
OpenStreetMap tile background) are supported.
"""

from arcline.dashboard.viz.layouts import LayoutMode, compute_layout
from arcline.dashboard.viz.plotly_graph import build_figure
from arcline.dashboard.viz.styles import kind_color, kind_icon

__all__ = [
    "LayoutMode",
    "compute_layout",
    "build_figure",
    "kind_color",
    "kind_icon",
]
