# -*- encoding: utf-8 -*-

"""
Tests for the Network Builder and Graph Mutators
------------------------------------------------

Exercises :class:`arcline.graph.builder.NetworkBuilder` and the
:class:`AbstractGraph` mutator surface provided by
:class:`NetworkXGraph` (``addNode`` / ``addEdge`` / ``updateNode`` /
``updateEdge`` / ``removeNode`` / ``removeEdge``).
"""

import pytest

from arcline.graph.builder import NetworkBuilder
from arcline.graph.library import CustomerNode, LaneEdge, PlantNode, SupplierNode


def test_build_minimal_graph() -> None:
    builder = NetworkBuilder()
    builder.add(SupplierNode(name = "S1", hashKey = "N-S1"))
    graph = builder.build()

    assert graph.numNodes == 1
    assert graph.numEdges == 0


def test_build_with_edges(sampleGraph) -> None:
    assert sampleGraph.numNodes == 3
    assert sampleGraph.numEdges == 2


def test_duplicate_hashkey_rejected() -> None:
    builder = NetworkBuilder()
    builder.add(SupplierNode(name = "S1", hashKey = "N-DUP"))

    with pytest.raises(ValueError):
        builder.add(SupplierNode(name = "S2", hashKey = "N-DUP"))


def test_orphan_edge_rejected() -> None:
    builder = NetworkBuilder()
    sIn = builder.add(SupplierNode(name = "S", hashKey = "N-S"))
    pIn = builder.add(PlantNode(name = "P", hashKey = "N-P"))

    orphan = PlantNode(name = "Orphan", hashKey = "N-ORPH")
    builder._edges.append(LaneEdge(
        name = "bad", hashKey = "E-BAD",
        srcNode = sIn, dstNode = orphan,
        distanceKm = 1.0, costPerUnit = 1.0,
        transitDays = 1.0, mode = "road",
    ))

    with pytest.raises(ValueError):
        builder.build()

    # silence unused-variable lint without changing behavior
    assert pIn.hashKey == "N-P"


def test_add_node_mutator(sampleGraph) -> None:
    newNode = SupplierNode(name = "S2", hashKey = "N-S2")
    before = sampleGraph.numNodes
    sampleGraph.addNode(newNode)

    assert sampleGraph.numNodes == before + 1
    assert sampleGraph.hasNode(newNode) is True


def test_update_node_mutator(sampleGraph) -> None:
    target = next(
        node for node in sampleGraph.nodes
        if node.hashKey == "N-S1"
    )
    updated = sampleGraph.updateNode(target, leadTimeDays = 99.0)

    assert updated.leadTimeDays == 99.0
    refreshed = next(
        node for node in sampleGraph.nodes
        if node.hashKey == "N-S1"
    )
    assert refreshed is updated
    assert refreshed.leadTimeDays == 99.0


def test_remove_node_mutator(sampleGraph) -> None:
    target = next(
        node for node in sampleGraph.nodes
        if node.hashKey == "N-C1"
    )
    before = sampleGraph.numNodes
    sampleGraph.removeNode(target)

    assert sampleGraph.numNodes == before - 1
    assert sampleGraph.hasNode(target) is False


def test_add_edge_mutator(sampleGraph) -> None:
    src = next(
        node for node in sampleGraph.nodes
        if node.hashKey == "N-S1"
    )
    dst = next(
        node for node in sampleGraph.nodes
        if node.hashKey == "N-P1"
    )

    parallel = LaneEdge(
        name = "S1->P1 #2", hashKey = "E-S1P1-ALT",
        srcNode = src, dstNode = dst,
        distanceKm = 110.0, costPerUnit = 2.7,
        transitDays = 2.5, mode = "rail",
    )

    before = sampleGraph.numEdges
    sampleGraph.addEdge(parallel)
    assert sampleGraph.numEdges == before + 1


def test_update_edge_endpoint_change_rejected(sampleGraph) -> None:
    edge = sampleGraph.edges[0]
    other = CustomerNode(name = "Other", hashKey = "N-OTHER")

    with pytest.raises(ValueError):
        sampleGraph.updateEdge(edge, srcNode = other)


def test_remove_edge_mutator(sampleGraph) -> None:
    edge = sampleGraph.edges[0]
    before = sampleGraph.numEdges
    sampleGraph.removeEdge(edge)

    assert sampleGraph.numEdges == before - 1


def test_graph_edges_by_key_uses_dst() -> None:
    """Regression: ``_edgesByKey`` keyed by (src, dst), not (src, src)."""

    builder = NetworkBuilder()
    src = builder.add(SupplierNode(name = "S1", hashKey = "N-S1"))
    dst = builder.add(PlantNode(name = "P1", hashKey = "N-P1"))
    edge = builder.connect(
        src, dst, name = "S1->P1", hashKey = "E-S1P1",
        distanceKm = 1.0, costPerUnit = 1.0,
        transitDays = 1.0, mode = "road",
    )
    graph = builder.build()

    bucket = graph._edgesByKey[edge.hashKey]
    assert ("N-S1", "N-P1") in bucket
    assert ("N-S1", "N-S1") not in bucket


def test_update_node_hashkey_rejected(sampleGraph) -> None:
    """Regression: changing hashKey via updateNode must raise."""

    target = next(
        node for node in sampleGraph.nodes
        if node.hashKey == "N-S1"
    )

    with pytest.raises(ValueError, match = "immutable"):
        sampleGraph.updateNode(target, hashKey = "N-OTHER")


def test_update_edge_hashkey_rejected(sampleGraph) -> None:
    """Regression: changing hashKey via updateEdge must raise."""

    edge = sampleGraph.edges[0]

    with pytest.raises(ValueError, match = "immutable"):
        sampleGraph.updateEdge(edge, hashKey = "E-OTHER")


def test_update_node_keeps_graph_in_sync(sampleGraph) -> None:
    """After updateNode, NetworkX vertex set must match the node list."""

    target = next(
        node for node in sampleGraph.nodes
        if node.hashKey == "N-S1"
    )
    sampleGraph.updateNode(target, leadTimeDays = 99.0)

    assert set(sampleGraph.G.nodes) == {
        n.hashKey for n in sampleGraph.nodes
    }
