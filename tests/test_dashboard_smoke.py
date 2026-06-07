# -*- encoding: utf-8 -*-

"""
Smoke Tests for the Dash Dashboard
----------------------------------

Marked with the ``dashboard`` marker; skipped at collection time if
the optional ``[dashboard]`` extras (dash, dash-bootstrap-components,
plotly) are not available.
"""

import pytest

try:
    import dash  # noqa: F401
    import dash_bootstrap_components as dbc
    import plotly  # noqa: F401

    from arcline.dashboard.app import create_app
    from arcline.dashboard.components.kpi_cards import make_kpi_strip
    from arcline.dashboard.components.node_form import make_node_form
    from arcline.dashboard.viz.layouts import compute_layout
    from arcline.dashboard.viz.plotly_graph import build_figure
except ImportError:
    pytest.skip(
        "dashboard extras not installed", allow_module_level = True,
    )


pytestmark = pytest.mark.dashboard


def _iter_children(node):
    """Walk a Dash component tree yielding every component."""

    yield node
    children = getattr(node, "children", None)
    if children is None:
        return

    if isinstance(children, (list, tuple)):
        for child in children:
            if child is None:
                continue
            yield from _iter_children(child)
    else:
        yield from _iter_children(children)


def test_create_app_without_project() -> None:
    app = create_app()
    assert app is not None
    assert app.layout is not None


def test_create_app_with_project(sample_project) -> None:
    app = create_app(projectPath = sample_project.path)
    from dash import html

    assert isinstance(app.layout, html.Div)


def test_node_form_renders_inputs_per_field() -> None:
    form = make_node_form("supplier")
    from dash import dcc

    input_like = (dbc.Input, dbc.Select, dbc.Switch, dcc.Input)
    inputs = [
        component for component in _iter_children(form)
        if isinstance(component, input_like)
    ]
    assert len(inputs) >= 3


def test_kpi_strip_renders_for_graph(sample_graph) -> None:
    row = make_kpi_strip(sample_graph)
    assert isinstance(row, dbc.Row)

    cards = [
        component for component in _iter_children(row)
        if isinstance(component, dbc.Col)
    ]
    distinct_kinds = { type(node).kind for node in sample_graph.nodes }
    assert len(cards) >= 2 + len(distinct_kinds)


def test_visualize_layouts(sample_graph) -> None:
    for mode in ("spring", "tiered", "geo"):
        layout = compute_layout(sample_graph, mode = mode)
        assert isinstance(layout, dict)
        assert len(layout) == sample_graph.numNodes


def test_build_figure_runs(sample_graph) -> None:
    fig = build_figure(sample_graph, mode = "spring")
    assert fig.data
