# -*- encoding: utf-8 -*-

"""
NetworkX-Backed Supply-Chain Network — Worked Example
-----------------------------------------------------

Builds a small directed multi-graph using :class:`NetworkXGraph` over
concrete subclasses of :class:`AbstractNode` and :class:`AbstractEdge`.
Demonstrates the new abstract-graph surface: explicit node and edge
object lists, materialisation via :meth:`buildGraph`, typed adjacency
queries that return :class:`AbstractNode` objects, multi-graph degree
counts, and the backend escape hatch (``g.G``) for direct NetworkX
algorithm calls.

Run from the repository root:

.. code-block:: console

    python examples/networkx_supply_chain.py
"""

from __future__ import annotations

from enum import Enum
from typing import ClassVar, Dict, Optional

import networkx as nx
from pydantic import Field

from arcline.graph.base import AbstractEdge, AbstractNode
from arcline.graph.backends.networkx import NetworkXGraph


class NodeType(str, Enum):
    """Supply-chain node classification."""
    SUPPLIER  = "supplier"
    PLANT     = "plant"
    WAREHOUSE = "warehouse"
    CUSTOMER  = "customer"


class TransportMode(str, Enum):
    """Logistics transport mode."""
    ROAD = "road"
    SEA  = "sea"
    AIR  = "air"
    RAIL = "rail"


class SupplyChainNode(AbstractNode):
    """
    Concrete supply-chain node with typed business attributes.

    Extends :class:`AbstractNode` with the dimensions that downstream
    optimisers and analytics typically slice on: classification
    (:class:`NodeType`), geographic region, purchase and materials
    grouping, and a soft capacity hint where applicable.
    """

    nodeType       : NodeType
    region         : str
    purchaseGroup  : Optional[str] = None
    materialsGroup : Optional[str] = None
    capacity       : Optional[float] = Field(default = None, ge = 0)

    _COLOR_MAP : ClassVar[Dict[NodeType, str]] = {
        NodeType.SUPPLIER  : "#1f77b4",
        NodeType.PLANT     : "#2ca02c",
        NodeType.WAREHOUSE : "#ff7f0e",
        NodeType.CUSTOMER  : "#d62728",
    }


    @property
    def imagePath(self) -> Optional[str]:
        """No custom icon is bundled with the reference payload."""
        return None


    @property
    def nodeColor(self) -> Optional[str]:
        """Pick a colour from a fixed palette keyed on the node type."""
        return self._COLOR_MAP.get(self.nodeType)


class SupplyChainLane(AbstractEdge):
    """
    Concrete supply-chain lane with typed logistics attributes.

    Extends :class:`AbstractEdge` with the cost and service-level
    fields that supply-chain optimisation problems consume as edge
    weights: lead time, transport cost, carrier identity, hard
    capacity, and the transport mode.
    """

    leadTime      : float = Field(ge = 0)
    transportCost : float = Field(ge = 0)
    carrier       : str
    capacity      : float = Field(gt = 0)
    mode          : TransportMode = TransportMode.ROAD

    _COLOR_MAP : ClassVar[Dict[TransportMode, str]] = {
        TransportMode.ROAD : "#7f7f7f",
        TransportMode.SEA  : "#1f77b4",
        TransportMode.AIR  : "#d62728",
        TransportMode.RAIL : "#2ca02c",
    }


    @property
    def edgeColor(self) -> Optional[str]:
        """Pick a colour from a fixed palette keyed on transport mode."""
        return self._COLOR_MAP.get(self.mode)


def buildNetwork() -> NetworkXGraph:
    """
    Construct and return a small reference supply-chain network.

    Two suppliers (APAC and EMEA) feed a single Mumbai plant, which
    ships to a Delhi distribution centre and on to a retail customer.
    The Helix → Mumbai lane is duplicated as both a sea and an air
    lane to exercise the multi-graph parallel-edge support.
    """
    supAcme = SupplyChainNode(
        name           = "Acme Polymers",
        hashKey        = "SUP_001",
        nodeType       = NodeType.SUPPLIER,
        region         = "APAC",
        purchaseGroup  = "PG_RAW_POLY",
    )
    supHelix = SupplyChainNode(
        name           = "Helix Resins",
        hashKey        = "SUP_002",
        nodeType       = NodeType.SUPPLIER,
        region         = "EMEA",
        purchaseGroup  = "PG_RAW_POLY",
    )
    pltMumbai = SupplyChainNode(
        name           = "Mumbai PlantNode",
        hashKey        = "PLT_001",
        nodeType       = NodeType.PLANT,
        region         = "APAC",
        materialsGroup = "MG_FORMULATED",
        capacity       = 50_000,
    )
    whDelhi = SupplyChainNode(
        name           = "Delhi DC",
        hashKey        = "WH_001",
        nodeType       = NodeType.WAREHOUSE,
        region         = "APAC",
    )
    cusRetail = SupplyChainNode(
        name           = "Retailer X",
        hashKey        = "CUS_001",
        nodeType       = NodeType.CUSTOMER,
        region         = "APAC",
    )

    nodes = [supAcme, supHelix, pltMumbai, whDelhi, cusRetail]

    edges = [
        SupplyChainLane(
            name = "Acme → Mumbai (road)", hashKey = "LANE_001",
            srcNode = supAcme, dstNode = pltMumbai,
            leadTime = 5.0, transportCost = 120.0,
            carrier = "BlueDart", capacity = 1000,
            mode = TransportMode.ROAD,
        ),
        SupplyChainLane(
            name = "Helix → Mumbai (sea)", hashKey = "LANE_002",
            srcNode = supHelix, dstNode = pltMumbai,
            leadTime = 21.0, transportCost = 450.0,
            carrier = "Maersk", capacity = 800,
            mode = TransportMode.SEA,
        ),
        SupplyChainLane(
            name = "Helix → Mumbai (air)", hashKey = "LANE_003",
            srcNode = supHelix, dstNode = pltMumbai,
            leadTime = 3.0, transportCost = 1800.0,
            carrier = "DHL", capacity = 200,
            mode = TransportMode.AIR,
        ),
        SupplyChainLane(
            name = "Mumbai → Delhi (own fleet)", hashKey = "LANE_004",
            srcNode = pltMumbai, dstNode = whDelhi,
            leadTime = 1.5, transportCost = 40.0,
            carrier = "OwnFleet", capacity = 5000,
        ),
        SupplyChainLane(
            name = "Delhi → Retailer X", hashKey = "LANE_005",
            srcNode = whDelhi, dstNode = cusRetail,
            leadTime = 0.5, transportCost = 15.0,
            carrier = "Delhivery", capacity = 2000,
        ),
    ]

    return NetworkXGraph(
        nodes = nodes,
        edges = edges,
        name  = "ReferenceNetwork",
    )


def main() -> None:
    g = buildNetwork()
    byKey = {n.hashKey : n for n in g.nodes}

    print("===== Topology =====")
    print(g)
    print(f"name      = {g.name}")
    print(f"numNodes  = {g.numNodes}")
    print(f"numEdges  = {g.numEdges}")

    print("\n===== Typed Node Access =====")
    plant = byKey["PLT_001"]
    print(f"plant         = {plant!r}")
    print(f"plant.region  = {plant.region}")
    print(f"plant.capacity= {plant.capacity}")
    print(f"plant.color   = {plant.nodeColor}")

    print("\n===== Adjacency (PlantNode) =====")
    print("predecessors = "
          f"{[n.hashKey for n in g.predecessors(plant)]}")
    print("successors   = "
          f"{[n.hashKey for n in g.successors(plant)]}")
    print("neighbors    = "
          f"{[n.hashKey for n in g.neighbors(plant)]}")

    print("\n===== Degree (PlantNode) =====")
    print(f"PLT_001 in / out / total = "
          f"{g.inDegree(plant)} / {g.outDegree(plant)} / {g.degree(plant)}")

    print("\n===== Edge Iteration =====")
    for edge in g.edges:
        print(f"  {edge.srcNode.hashKey:>7} -> {edge.dstNode.hashKey:<7}  "
              f"leadTime={edge.leadTime:>5.1f}d  "
              f"cost={edge.transportCost:>7.1f}  "
              f"carrier={edge.carrier:<10}  mode={edge.mode.value}")

    print("\n===== Membership / Edge Existence =====")
    print(f"plant in g                 = {plant in g}")
    print(f"hasEdge(SUP_001 -> PLT_001) = {g.hasEdge(byKey['SUP_001'], plant)}")
    print(f"hasEdge(SUP_002 -> PLT_001) = {g.hasEdge(byKey['SUP_002'], plant)}")
    print(f"hasEdge(PLT_001 -> SUP_001) = {g.hasEdge(plant, byKey['SUP_001'])}")

    print("\n===== Group Slice via Node List (no built-in index) =====")
    apacNodes = [n for n in g.nodes if n.region == "APAC"]
    print(f"APAC nodes     = {[n.hashKey for n in apacNodes]}")
    suppliers = [n for n in g.nodes if n.nodeType is NodeType.SUPPLIER]
    print(f"SupplierNode nodes = {[n.hashKey for n in suppliers]}")

    print("\n===== Backend Escape Hatch =====")
    print(f"backend type   = {type(g.G).__name__}")
    cheapest = nx.shortest_path(g.G, "SUP_002", "CUS_001", weight = "transportCost")
    fastest  = nx.shortest_path(g.G, "SUP_002", "CUS_001", weight = "leadTime")
    print(f"cheapest path  = {' -> '.join(cheapest)}")
    print(f"fastest  path  = {' -> '.join(fastest)}")

    print("\n===== Targeted Edge Removal (Multigraph) =====")
    air = next(e for e in g.edges if e.hashKey == "LANE_003")
    print(f"before removal: numEdges={g.numEdges}, "
          f"Helix -> Mumbai parallels="
          f"{g.G.number_of_edges('SUP_002', 'PLT_001')}")
    g.removeEdge(air)
    print(f"after  removal: numEdges={g.numEdges}, "
          f"Helix -> Mumbai parallels="
          f"{g.G.number_of_edges('SUP_002', 'PLT_001')}")


if __name__ == "__main__":
    main()
