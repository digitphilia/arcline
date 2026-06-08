# -*- encoding: utf-8 -*-

"""
Full Taxonomy Showcase
======================

A single runnable example that exercises **every** built-in concrete
class in :mod:`arcline.graph.library` and every Enum in
:mod:`arcline.graph.enums`, so a new contributor can read one file and
see the complete shipped surface in context:

* All four node kinds: :class:`SupplierNode`, :class:`PlantNode`,
  :class:`WarehouseNode`, :class:`CustomerNode`.
* All three edge kinds: :class:`LaneEdge`, :class:`ProductionEdge`,
  :class:`StorageEdge`.
* The capability flag API (``node.supports("canManufacture")``) used
  to introspect a node without an ``isinstance`` ladder.
* Enum-backed categorical fields: :class:`TransportationMode`,
  :class:`FacilityStatus`, :class:`OwnershipType`,
  :class:`StorageType`, :class:`LaneServiceLevel`,
  :class:`CustomerSegment`.
* Persistence as a portable :class:`Project` directory and round-trip
  through :func:`Project.open`.

Run from the repository root:

.. code-block:: console

    python examples/full_taxonomy_demo.py --output ./full_taxonomy_demo
    arcline dashboard ./full_taxonomy_demo
"""

from __future__ import annotations

import argparse
from pathlib import Path

from arcline import (
    CustomerNode, CustomerSegment,
    FacilityStatus,
    LaneEdge, LaneServiceLevel,
    OwnershipType,
    PlantNode, ProductionEdge,
    StorageEdge, StorageType,
    SupplierNode,
    TransportationMode,
    WarehouseNode,
)
from arcline.graph.builder import NetworkBuilder
from arcline.io import Project


def buildShowcase() -> NetworkBuilder:
    """
    Assemble a small five-node network that touches every node and
    edge kind in the shipped taxonomy.
    """

    builder = NetworkBuilder()

    sup = builder.add(SupplierNode(
        name = "Acme Steel", hashKey = "N-SUP-ACME",
        latitude = 12.97, longitude = 77.59,
        leadTimeDays = 3.0, reliabilityScore = 0.95,
    ))

    plant = builder.add(PlantNode(
        name = "Bengaluru Plant", hashKey = "N-PLT-BLR",
        latitude = 12.95, longitude = 77.62,
        productionRatePerHr = 120.0,
        minCapacity = 500.0, maxCapacity = 10_000.0,
        operatingCostPerHr = 250.0,
        status = FacilityStatus.OPEN,
        ownership = OwnershipType.OWNED,
    ))

    warehouse = builder.add(WarehouseNode(
        name = "Whitefield DC", hashKey = "N-WH-WFD",
        latitude = 12.98, longitude = 77.74,
        minCapacity = 0.0, maxCapacity = 25_000.0,
        storageType = StorageType.AMBIENT,
        ownership = OwnershipType.LEASED,
    ))

    cust = builder.add(CustomerNode(
        name = "Retail Customer A", hashKey = "N-CUST-A",
        latitude = 13.03, longitude = 77.57,
        demandMean = 350.0, demandStd = 45.0,
        segment = CustomerSegment.RETAIL,
    ))

    builder.connect(
        sup, plant, cls = LaneEdge,
        name = "Acme -> Plant", hashKey = "E-L-SP",
        distanceKm = 220.0, costPerUnit = 2.50, transitDays = 1.5,
        mode = TransportationMode.ROAD,
        serviceLevel = LaneServiceLevel.STANDARD,
    )
    builder.connect(
        plant, plant, cls = ProductionEdge,
        name = "Plant production loop", hashKey = "E-P-PLT",
        costPerUnit = 0.80,
    )
    builder.connect(
        plant, warehouse, cls = LaneEdge,
        name = "Plant -> Whitefield", hashKey = "E-L-PW",
        distanceKm = 15.0, costPerUnit = 0.40, transitDays = 0.2,
        mode = TransportationMode.RAIL,
        serviceLevel = LaneServiceLevel.EXPEDITED,
    )
    builder.connect(
        warehouse, warehouse, cls = StorageEdge,
        name = "Whitefield holding", hashKey = "E-S-WFD",
        storageType = StorageType.AMBIENT,
    )
    builder.connect(
        warehouse, cust, cls = LaneEdge,
        name = "Whitefield -> Retail", hashKey = "E-L-WC",
        distanceKm = 40.0, costPerUnit = 1.10, transitDays = 0.5,
        mode = TransportationMode.ROAD,
    )

    return builder


def printCapabilityMatrix(graph) -> None:
    """
    Pretty-print the capability matrix for every node in the network,
    demonstrating ``node.supports(...)`` as an alternative to
    ``isinstance`` ladders.
    """

    capabilities = (
        "canShip", "canStore", "canManufacture", "canDemand",
    )
    header = f"{'NODE':<22}" + "".join(f"{c:>16}" for c in capabilities)
    print(header)
    print("-" * len(header))
    for node in graph.nodes:
        row = f"{type(node).__name__ + ' (' + node.name + ')':<22}"
        row += "".join(
            f"{str(node.supports(cap)):>16}" for cap in capabilities
        )
        print(row)


def parseArgs() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description = "Build a full-taxonomy showcase project.",
    )
    parser.add_argument(
        "--output", type = Path, default = Path("./full_taxonomy_demo"),
        help = "Destination project directory.",
    )
    return parser.parse_args()


def main() -> int:
    args = parseArgs()

    builder = buildShowcase()
    graph = builder.build(backend = "networkx")

    print(f"\nBuilt {len(graph.nodes)} nodes, {len(graph.edges)} edges.\n")
    printCapabilityMatrix(graph)

    proj = Project.fromGraph(
        graph, path = args.output, name = "full-taxonomy",
        description = "Showcase covering all built-in *Node / *Edge kinds.",
    )
    proj.save()

    print(
        f"\nProject written to: {args.output.resolve()}\n"
        f"Open it in the dashboard with:\n"
        f"    arcline dashboard {args.output}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
