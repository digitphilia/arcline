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
    makeEdgeTable,
    makeNodeTable,
)
from arcline.dashboard.components.edge_form import makeEdgeForm
from arcline.dashboard.components.kpi_cards import makeKpiStrip
from arcline.dashboard.components.navbar import makeNavbar
from arcline.dashboard.components.node_form import inferInput, makeNodeForm

__all__ = [
    "makeNavbar",
    "makeNodeForm",
    "makeEdgeForm",
    "makeNodeTable",
    "makeEdgeTable",
    "makeKpiStrip",
    "inferInput",
]
