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
from arcline.graph.library import Customer, Lane, Plant, Supplier


def test_build_minimal_graph() -> None:
    builder = NetworkBuilder()
    builder.add(Supplier(name = "S1", hashKey = "N-S1"))
    graph = builder.build()

    assert graph.numNodes == 1
    assert graph.numEdges == 0


def test_build_with_edges(sample_graph) -> None:
    assert sample_graph.numNodes == 3
    assert sample_graph.numEdges == 2


def test_duplicate_hashkey_rejected() -> None:
    builder = NetworkBuilder()
    builder.add(Supplier(name = "S1", hashKey = "N-DUP"))

    with pytest.raises(ValueError):
        builder.add(Supplier(name = "S2", hashKey = "N-DUP"))


def test_orphan_edge_rejected() -> None:
    builder = NetworkBuilder()
    s_in = builder.add(Supplier(name = "S", hashKey = "N-S"))
    p_in = builder.add(Plant(name = "P", hashKey = "N-P"))

    orphan = Plant(name = "Orphan", hashKey = "N-ORPH")
    builder._edges.append(Lane(
        name = "bad", hashKey = "E-BAD",
        srcNode = s_in, dstNode = orphan,
        distanceKm = 1.0, costPerUnit = 1.0,
        transitDays = 1.0, mode = "road",
    ))

    with pytest.raises(ValueError):
        builder.build()

    # silence unused-variable lint without changing behavior
    assert p_in.hashKey == "N-P"


def test_add_node_mutator(sample_graph) -> None:
    new_node = Supplier(name = "S2", hashKey = "N-S2")
    before = sample_graph.numNodes
    sample_graph.addNode(new_node)

    assert sample_graph.numNodes == before + 1
    assert sample_graph.hasNode(new_node) is True


def test_update_node_mutator(sample_graph) -> None:
    target = next(
        node for node in sample_graph.nodes
        if node.hashKey == "N-S1"
    )
    updated = sample_graph.updateNode(target, leadTimeDays = 99.0)

    assert updated.leadTimeDays == 99.0
    refreshed = next(
        node for node in sample_graph.nodes
        if node.hashKey == "N-S1"
    )
    assert refreshed is updated
    assert refreshed.leadTimeDays == 99.0


def test_remove_node_mutator(sample_graph) -> None:
    target = next(
        node for node in sample_graph.nodes
        if node.hashKey == "N-C1"
    )
    before = sample_graph.numNodes
    sample_graph.removeNode(target)

    assert sample_graph.numNodes == before - 1
    assert sample_graph.hasNode(target) is False


def test_add_edge_mutator(sample_graph) -> None:
    src = next(
        node for node in sample_graph.nodes
        if node.hashKey == "N-S1"
    )
    dst = next(
        node for node in sample_graph.nodes
        if node.hashKey == "N-P1"
    )

    parallel = Lane(
        name = "S1->P1 #2", hashKey = "E-S1P1-ALT",
        srcNode = src, dstNode = dst,
        distanceKm = 110.0, costPerUnit = 2.7,
        transitDays = 2.5, mode = "rail",
    )

    before = sample_graph.numEdges
    sample_graph.addEdge(parallel)
    assert sample_graph.numEdges == before + 1


def test_update_edge_endpoint_change_rejected(sample_graph) -> None:
    edge = sample_graph.edges[0]
    other = Customer(name = "Other", hashKey = "N-OTHER")

    with pytest.raises(ValueError):
        sample_graph.updateEdge(edge, srcNode = other)


def test_remove_edge_mutator(sample_graph) -> None:
    edge = sample_graph.edges[0]
    before = sample_graph.numEdges
    sample_graph.removeEdge(edge)

    assert sample_graph.numEdges == before - 1


def test_graph_edges_by_key_uses_dst() -> None:
    """Regression: ``_edgesByKey`` keyed by (src, dst), not (src, src)."""

    builder = NetworkBuilder()
    src = builder.add(Supplier(name = "S1", hashKey = "N-S1"))
    dst = builder.add(Plant(name = "P1", hashKey = "N-P1"))
    edge = builder.connect(
        src, dst, name = "S1->P1", hashKey = "E-S1P1",
        distanceKm = 1.0, costPerUnit = 1.0,
        transitDays = 1.0, mode = "road",
    )
    graph = builder.build()

    bucket = graph._edgesByKey[edge.hashKey]
    assert ("N-S1", "N-P1") in bucket
    assert ("N-S1", "N-S1") not in bucket


def test_update_node_hashkey_rejected(sample_graph) -> None:
    """Regression: changing hashKey via updateNode must raise."""

    target = next(
        node for node in sample_graph.nodes
        if node.hashKey == "N-S1"
    )

    with pytest.raises(ValueError, match = "immutable"):
        sample_graph.updateNode(target, hashKey = "N-OTHER")


def test_update_edge_hashkey_rejected(sample_graph) -> None:
    """Regression: changing hashKey via updateEdge must raise."""

    edge = sample_graph.edges[0]

    with pytest.raises(ValueError, match = "immutable"):
        sample_graph.updateEdge(edge, hashKey = "E-OTHER")


def test_update_node_keeps_graph_in_sync(sample_graph) -> None:
    """After updateNode, NetworkX vertex set must match the node list."""

    target = next(
        node for node in sample_graph.nodes
        if node.hashKey == "N-S1"
    )
    sample_graph.updateNode(target, leadTimeDays = 99.0)

    assert set(sample_graph.G.nodes) == {
        n.hashKey for n in sample_graph.nodes
    }
