# -*- encoding: utf-8 -*-

"""
Tests for the modernized dashboard: theme tokens, graph
serialization for the D3 canvas, and the :class:`NetworkCanvas`
custom-component wrapper.
"""

import pytest


pytest.importorskip("dash")
pytest.importorskip("dash_bootstrap_components")


def test_canvasTheme_dark_has_expected_keys() -> None:
    from arcline.dashboard.theme import canvasTheme

    theme = canvasTheme("dark")
    for key in (
        "bg", "surface", "border", "text", "accent",
        "edge", "edgeHighlight", "nodeStroke",
        "selectionRing", "pendingEdge",
    ):
        assert key in theme, f"missing {key}"
        assert isinstance(theme[key], str)


def test_canvasTheme_light_differs_from_dark() -> None:
    from arcline.dashboard.theme import canvasTheme

    dark = canvasTheme("dark")
    light = canvasTheme("light")
    assert dark != light
    assert dark["bg"] != light["bg"]


def test_canvasTheme_unknown_falls_back_to_dark() -> None:
    from arcline.dashboard.theme import canvasTheme

    fallback = canvasTheme("space-grey")
    dark = canvasTheme("dark")
    assert fallback == dark


def test_NetworkCanvas_namespace_and_type() -> None:
    from arcline.dashboard.d3 import NetworkCanvas

    component = NetworkCanvas(
        id = "viz", nodes = [], edges = [],
        theme = {"bg": "#000"}, layoutMode = "force",
    )
    assert component._namespace == "arcline_d3"
    assert component._type == "NetworkCanvas"
    assert component.id == "viz"
    assert component.nodes == []


def test_NetworkCanvas_drops_undefined_props() -> None:
    from arcline.dashboard.d3 import NetworkCanvas

    component = NetworkCanvas(id = "x")
    payload = component.to_plotly_json()
    assert payload["props"].get("id") == "x"
    # only id was set; nodes/edges should not appear
    assert "nodes" not in payload["props"]
    assert "edges" not in payload["props"]


def test_serializeGraph_round_trip(tmp_path) -> None:
    from arcline.dashboard.theme import serializeGraph
    from arcline.graph.builder import NetworkBuilder
    from arcline.graph.library.lane import LaneEdge
    from arcline.graph.library.plant import PlantNode
    from arcline.graph.library.supplier import SupplierNode

    builder = NetworkBuilder()
    src = builder.add(
        SupplierNode(
            name = "S1", hashKey = "N-S1",
            latitude = 12.97, longitude = 77.59,
        )
    )
    dst = builder.add(PlantNode(name = "P1", hashKey = "N-P1"))
    builder.connect(
        src, dst, cls = LaneEdge, hashKey = "E-S1P1",
        name = "S1-P1",
        transitDays = 2.0, distanceKm = 40.0,
    )
    graph = builder.build()

    serialized = serializeGraph(graph, iconBase = "/assets/icons/")
    assert len(serialized["nodes"]) == 2
    assert len(serialized["edges"]) == 1

    nodeKeys = {n["hashKey"] for n in serialized["nodes"]}
    assert nodeKeys == {"N-S1", "N-P1"}

    supplier = next(
        n for n in serialized["nodes"] if n["hashKey"] == "N-S1"
    )
    assert supplier["kind"] == "supplier"
    assert supplier["color"].startswith("#")
    assert supplier["icon"].startswith("/assets/icons/")
    assert supplier["lat"] == 12.97 and supplier["lng"] == 77.59

    edge = serialized["edges"][0]
    assert edge["srcKey"] == "N-S1"
    assert edge["dstKey"] == "N-P1"
    assert "color" in edge and "width" in edge


def test_serializeGraph_handles_missing_coords() -> None:
    """Nodes without lat/lon serialize lat=None / lng=None cleanly."""
    from arcline.dashboard.theme import serializeGraph
    from arcline.graph.builder import NetworkBuilder
    from arcline.graph.library.customer import CustomerNode

    builder = NetworkBuilder()
    builder.add(CustomerNode(name = "C1", hashKey = "N-C1"))
    graph = builder.build()

    serialized = serializeGraph(graph)
    assert serialized["nodes"][0]["lat"] is None
    assert serialized["nodes"][0]["lng"] is None
