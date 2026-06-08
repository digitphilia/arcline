# -*- encoding: utf-8 -*-

"""
Random Supply-Chain Network Generator
=====================================

A runnable example that synthesises a random four-tier supply chain
(SupplierNode -> PlantNode -> WarehouseNode -> CustomerNode), persists it as a full
:mod:`arcline` project on disk, and **additionally** dumps the bulk
``nodes.parquet`` / ``edges.parquet`` pair so the same data is
available to downstream Pandas / Spark consumers.

Usage
-----

.. code-block:: shell

    # 1. generate the network (defaults: 6/4/3/8 entities, seed 42)
    python examples/random_network.py --output ./demo_network

    # 2. open it in the dashboard (uses the manifest + nodes.json /
    #    edges.json that the script wrote next to the parquet pair)
    arcline dashboard ./demo_network

    # OR run the dashboard module directly (same effect):
    python -m arcline.dashboard --project ./demo_network

The project directory after a successful run::

    demo_network/
        manifest.yaml        <- project metadata
        nodes.json           <- canonical, git-friendly schema
        edges.json
        nodes.parquet        <- bulk format (this script's deliverable)
        edges.parquet
        icons/               <- empty placeholder
        scenarios/           <- empty placeholder
        .gitignore
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import List, Tuple

from arcline import (
    CustomerNode, LaneEdge, PlantNode, SupplierNode,
    TransportationMode, WarehouseNode,
)
from arcline.graph.builder import NetworkBuilder
from arcline.io import Project, toParquet


_BENGALURU_LATLON : Tuple[float, float] = (12.97, 77.59)
_LATLON_JITTER : float = 8.0


def _jitterLatLon(rng : random.Random) -> Tuple[float, float]:
    """Return a (lat, lon) pair within ``+/- _LATLON_JITTER`` of Bengaluru."""

    lat = _BENGALURU_LATLON[0] + rng.uniform(-_LATLON_JITTER, _LATLON_JITTER)
    lon = _BENGALURU_LATLON[1] + rng.uniform(-_LATLON_JITTER, _LATLON_JITTER)
    return round(lat, 4), round(lon, 4)


def _buildSuppliers(builder : NetworkBuilder, count : int,
                    rng : random.Random) -> List[SupplierNode]:
    out : List[SupplierNode] = []
    for index in range(count):
        lat, lon = _jitterLatLon(rng)
        node = SupplierNode(
            name = f"SupplierNode-{index + 1:02d}",
            hashKey = f"N-S{index + 1:02d}",
            latitude = lat,
            longitude = lon,
            leadTimeDays = round(rng.uniform(1.0, 10.0), 2),
            reliabilityScore = round(rng.uniform(0.80, 0.99), 3),
        )
        out.append(builder.add(node))
    return out


def _buildPlants(builder : NetworkBuilder, count : int,
                 rng : random.Random) -> List[PlantNode]:
    out : List[PlantNode] = []
    for index in range(count):
        lat, lon = _jitterLatLon(rng)
        maxCap = float(rng.randint(5_000, 25_000))
        node = PlantNode(
            name = f"PlantNode-{index + 1:02d}",
            hashKey = f"N-P{index + 1:02d}",
            latitude = lat,
            longitude = lon,
            productionRatePerHr = round(rng.uniform(50.0, 300.0), 2),
            minCapacity = 0.0,
            maxCapacity = maxCap,
        )
        out.append(builder.add(node))
    return out


def _buildWarehouses(builder : NetworkBuilder, count : int,
                     rng : random.Random) -> List[WarehouseNode]:
    out : List[WarehouseNode] = []
    for index in range(count):
        lat, lon = _jitterLatLon(rng)
        maxCap = float(rng.randint(10_000, 60_000))
        node = WarehouseNode(
            name = f"DC-{index + 1:02d}",
            hashKey = f"N-W{index + 1:02d}",
            latitude = lat,
            longitude = lon,
            minCapacity = 0.0,
            maxCapacity = maxCap,
        )
        out.append(builder.add(node))
    return out


def _buildCustomers(builder : NetworkBuilder, count : int,
                    rng : random.Random) -> List[CustomerNode]:
    out : List[CustomerNode] = []
    for index in range(count):
        lat, lon = _jitterLatLon(rng)
        mean = round(rng.uniform(50.0, 500.0), 2)
        node = CustomerNode(
            name = f"CustomerNode-{index + 1:02d}",
            hashKey = f"N-C{index + 1:02d}",
            latitude = lat,
            longitude = lon,
            demandMean = mean,
            demandStd = round(mean * rng.uniform(0.05, 0.25), 2),
        )
        out.append(builder.add(node))
    return out


_MODES : Tuple[TransportationMode, ...] = (
    TransportationMode.ROAD,
    TransportationMode.RAIL,
    TransportationMode.SEA,
    TransportationMode.AIR,
)


def _connectTier(builder : NetworkBuilder, upstream : List, downstream : List,
                 fanout : int, prefix : str,
                 rng : random.Random) -> int:
    """
    Connect every ``upstream`` node to ``fanout`` random ``downstream``
    nodes via a :class:`LaneEdge`. Returns the number of edges created.
    """

    edgeCount = 0
    for src in upstream:
        targets = rng.sample(downstream, k = min(fanout, len(downstream)))
        for dst in targets:
            edgeCount += 1
            builder.connect(
                src, dst, cls = LaneEdge,
                name = f"{prefix}-{edgeCount:04d}",
                hashKey = f"E-{prefix}-{edgeCount:04d}",
                distanceKm = round(rng.uniform(50.0, 2000.0), 1),
                costPerUnit = round(rng.uniform(0.5, 12.0), 2),
                transitDays = round(rng.uniform(0.5, 14.0), 1),
                mode = rng.choice(_MODES),
            )
    return edgeCount


def generateNetwork(
        suppliers : int = 6,
        plants : int = 4,
        warehouses : int = 3,
        customers : int = 8,
        seed : int = 42,
) -> NetworkBuilder:
    """
    Build a random four-tier supply chain and return the populated
    :class:`NetworkBuilder`.

    Tiers connect: SupplierNode -> PlantNode -> WarehouseNode -> CustomerNode with
    deterministic fanouts (each upstream node feeds 2 downstream
    nodes) so the resulting network is connected for any reasonable
    tier sizing.
    """

    rng = random.Random(seed)
    builder = NetworkBuilder()

    sups = _buildSuppliers(builder, suppliers, rng)
    plts = _buildPlants(builder, plants, rng)
    whs  = _buildWarehouses(builder, warehouses, rng)
    cust = _buildCustomers(builder, customers, rng)

    n1 = _connectTier(builder, sups, plts, fanout = 2, prefix = "SP", rng = rng)
    n2 = _connectTier(builder, plts, whs,  fanout = 2, prefix = "PW", rng = rng)
    n3 = _connectTier(builder, whs,  cust, fanout = 3, prefix = "WC", rng = rng)

    print(
        f"  built {suppliers + plants + warehouses + customers} nodes "
        f"({suppliers}S + {plants}P + {warehouses}W + {customers}C) "
        f"and {n1 + n2 + n3} edges ({n1} S->P, {n2} P->W, {n3} W->C).",
    )
    return builder


def saveProjectAndParquet(builder : NetworkBuilder, output : Path) -> Path:
    """
    Persist the builder's network as a full :mod:`arcline` project
    **and** dump the bulk ``nodes.parquet`` / ``edges.parquet`` pair
    inside the same directory.
    """

    output = Path(output).resolve()
    if output.exists() and (output / "manifest.yaml").exists():
        raise FileExistsError(
            f"Refusing to overwrite existing project at {output}; "
            f"pass a different --output or delete the directory first.",
        )

    graph = builder.build(backend = "networkx")
    project = Project.fromGraph(
        graph, path = output,
        name = output.name,
        description = "Synthetic four-tier supply chain (random generator).",
    )

    nodesParquet = output / "nodes.parquet"
    edgesParquet = output / "edges.parquet"
    toParquet(
        nodes = project.nodes, edges = project.edges,
        nodesPath = nodesParquet, edgesPath = edgesParquet,
    )

    print(f"  project saved to {output}")
    print(f"     manifest      : {output / 'manifest.yaml'}")
    print(f"     nodes (json)  : {output / 'nodes.json'}")
    print(f"     edges (json)  : {output / 'edges.json'}")
    print(f"     nodes (parq)  : {nodesParquet}")
    print(f"     edges (parq)  : {edgesParquet}")
    return output


def main(argv : List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description = "Generate a random arcline supply-chain project.",
    )
    parser.add_argument(
        "--output", "-o", type = Path, default = Path("./demo_network"),
        help = "Project directory to create (default: ./demo_network).",
    )
    parser.add_argument("--suppliers",  type = int, default = 6)
    parser.add_argument("--plants",     type = int, default = 4)
    parser.add_argument("--warehouses", type = int, default = 3)
    parser.add_argument("--customers",  type = int, default = 8)
    parser.add_argument(
        "--seed", type = int, default = 42,
        help = "RNG seed for reproducibility (default: 42).",
    )
    args = parser.parse_args(argv)

    print(f"generating network (seed={args.seed}) ...")
    builder = generateNetwork(
        suppliers = args.suppliers,
        plants = args.plants,
        warehouses = args.warehouses,
        customers = args.customers,
        seed = args.seed,
    )

    saveProjectAndParquet(builder, args.output)

    print("")
    print("next: launch the dashboard against this project:")
    print(f"    arcline dashboard {args.output}")
    print(f"    # or: python -m arcline.dashboard --project {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
