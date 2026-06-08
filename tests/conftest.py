# -*- encoding: utf-8 -*-

"""
Shared pytest Fixtures
----------------------

Common fixtures exposed to every test module in the arcline test
suite. Fixtures cover temporary project directories, a canonical
three-node sample graph (supplier-plant-customer), and the
:class:`arcline.io.Project` round-trip persistence of that graph.
"""

from pathlib import Path
from typing import List

import pytest

from arcline.graph.backends.networkx import NetworkXGraph
from arcline.graph.base.edges import AbstractEdge
from arcline.graph.base.nodes import AbstractNode
from arcline.graph.library import (
    CustomerNode,
    LaneEdge,
    PlantNode,
    SupplierNode,
)
from arcline.io import Project


@pytest.fixture
def tmpProjectDir(tmp_path : Path) -> Path:
    """Fresh temp directory for a project under pytest's tmp_path."""

    return tmp_path / "proj"


@pytest.fixture
def sampleNodes() -> List[AbstractNode]:
    """Three typed nodes covering supplier, plant, customer."""

    return [
        SupplierNode(
            name = "S1", hashKey = "N-S1", leadTimeDays = 3.0,
            latitude = 12.97, longitude = 77.59,
        ),
        PlantNode(
            name = "P1", hashKey = "N-P1", maxCapacity = 1000.0
        ),
        CustomerNode(
            name = "C1", hashKey = "N-C1", demandMean = 50.0
        ),
    ]


@pytest.fixture
def sampleEdges(
        sampleNodes : List[AbstractNode]
) -> List[AbstractEdge]:
    """Two lanes wiring the sample nodes into a linear chain."""

    src, plant, cust = sampleNodes
    return [
        LaneEdge(
            name = "S1->P1", hashKey = "E-S1P1",
            srcNode = src, dstNode = plant,
            distanceKm = 100.0, costPerUnit = 2.5,
            transitDays = 2.0, mode = "ROAD",
        ),
        LaneEdge(
            name = "P1->C1", hashKey = "E-P1C1",
            srcNode = plant, dstNode = cust,
            distanceKm = 50.0, costPerUnit = 1.5,
            transitDays = 1.0, mode = "ROAD",
        ),
    ]


@pytest.fixture
def sampleGraph(
        sampleNodes : List[AbstractNode],
        sampleEdges : List[AbstractEdge]
) -> NetworkXGraph:
    """A populated :class:`NetworkXGraph` from the sample fixtures."""

    return NetworkXGraph(
        nodes = list(sampleNodes), edges = list(sampleEdges)
    )


@pytest.fixture
def sampleProject(
        sampleGraph : NetworkXGraph, tmpProjectDir : Path
) -> Project:
    """Persist the sample graph to disk and yield the project."""

    return Project.fromGraph(
        sampleGraph, tmpProjectDir,
        name = "sample", description = "pytest fixture",
    )
