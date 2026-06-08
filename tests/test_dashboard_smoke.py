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

    from arcline.dashboard.app import createApp
    from arcline.dashboard.components.kpi_cards import makeKpiStrip
    from arcline.dashboard.components.node_form import makeNodeForm
    from arcline.dashboard.viz.layouts import computeLayout
    from arcline.dashboard.viz.plotly_graph import buildFigure
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
    app = createApp()
    assert app is not None
    assert app.layout is not None


def test_create_app_with_project(sampleProject) -> None:
    app = createApp(projectPath = sampleProject.path)
    from dash import html

    assert isinstance(app.layout, html.Div)


def test_node_form_renders_inputs_per_field() -> None:
    form = makeNodeForm("supplier")
    from dash import dcc

    inputLike = (dbc.Input, dbc.Select, dbc.Switch, dcc.Input)
    inputs = [
        component for component in _iter_children(form)
        if isinstance(component, inputLike)
    ]
    assert len(inputs) >= 3


def test_kpi_strip_renders_for_graph(sampleGraph) -> None:
    row = makeKpiStrip(sampleGraph)
    assert isinstance(row, dbc.Row)

    cards = [
        component for component in _iter_children(row)
        if isinstance(component, dbc.Col)
    ]
    distinctKinds = { type(node).kind for node in sampleGraph.nodes }
    assert len(cards) >= 2 + len(distinctKinds)


def test_visualize_layouts(sampleGraph) -> None:
    for mode in ("spring", "tiered", "geo"):
        layout = computeLayout(sampleGraph, mode = mode)
        assert isinstance(layout, dict)
        assert len(layout) == sampleGraph.numNodes


def test_build_figure_runs(sampleGraph) -> None:
    fig = buildFigure(sampleGraph, mode = "spring")
    assert fig.data
