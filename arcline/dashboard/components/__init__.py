# -*- encoding: utf-8 -*-

"""
Dashboard UI Component Library
==============================

Reusable Dash + dash-bootstrap-components widgets used across the
dashboard pages: the top navigation bar, dynamic node / edge forms
auto-generated from pydantic schemas, ag-grid powered data tables,
and KPI summary cards.
"""

from arcline.dashboard.components.data_table import (
    make_edge_table,
    make_node_table,
)
from arcline.dashboard.components.edge_form import make_edge_form
from arcline.dashboard.components.kpi_cards import make_kpi_strip
from arcline.dashboard.components.navbar import make_navbar
from arcline.dashboard.components.node_form import infer_input, make_node_form

__all__ = [
    "make_navbar",
    "make_node_form",
    "make_edge_form",
    "make_node_table",
    "make_edge_table",
    "make_kpi_strip",
    "infer_input",
]
