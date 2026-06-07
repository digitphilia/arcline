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
from arcline.graph.library import Customer, Lane, Plant, Supplier
from arcline.io import Project


@pytest.fixture
def tmp_project_dir(tmp_path : Path) -> Path:
    """Fresh temp directory for a project under pytest's tmp_path."""

    return tmp_path / "proj"


@pytest.fixture
def sample_nodes() -> List[AbstractNode]:
    """Three typed nodes covering supplier, plant, customer."""

    return [
        Supplier(
            name = "S1", hashKey = "N-S1", leadTimeDays = 3.0,
            latitude = 12.97, longitude = 77.59,
        ),
        Plant(name = "P1", hashKey = "N-P1", maxCapacity = 1000.0),
        Customer(name = "C1", hashKey = "N-C1", demandMean = 50.0),
    ]


@pytest.fixture
def sample_edges(
        sample_nodes : List[AbstractNode]
) -> List[AbstractEdge]:
    """Two lanes wiring the sample nodes into a linear chain."""

    src, plant, cust = sample_nodes
    return [
        Lane(
            name = "S1->P1", hashKey = "E-S1P1",
            srcNode = src, dstNode = plant,
            distanceKm = 100.0, costPerUnit = 2.5,
            transitDays = 2.0, mode = "road",
        ),
        Lane(
            name = "P1->C1", hashKey = "E-P1C1",
            srcNode = plant, dstNode = cust,
            distanceKm = 50.0, costPerUnit = 1.5,
            transitDays = 1.0, mode = "road",
        ),
    ]


@pytest.fixture
def sample_graph(
        sample_nodes : List[AbstractNode],
        sample_edges : List[AbstractEdge]
) -> NetworkXGraph:
    """A populated :class:`NetworkXGraph` from the sample fixtures."""

    return NetworkXGraph(
        nodes = list(sample_nodes), edges = list(sample_edges)
    )


@pytest.fixture
def sample_project(
        sample_graph : NetworkXGraph, tmp_project_dir : Path
) -> Project:
    """Persist the sample graph to disk and yield the project."""

    return Project.fromGraph(
        sample_graph, tmp_project_dir,
        name = "sample", description = "pytest fixture",
    )
