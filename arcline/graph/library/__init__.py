# -*- encoding: utf-8 -*-

"""
Built-in Supply-Chain Taxonomy
==============================

Concrete subclasses of :class:`arcline.graph.base.AbstractNode` and
:class:`arcline.graph.base.AbstractEdge` shipped with the package, plus
the abstract intermediate bases that hold their shared structure.
Importing this subpackage triggers the registry side-effects that make
every shipped ``kind`` resolvable via :mod:`arcline.graph.registry`.
"""

from arcline.graph.library._intermediates import (
    DemandNode,
    FacilityNode,
    FlowEdge,
    SourceNode,
    TransportEdge,
)
from arcline.graph.library.customer import CustomerNode
from arcline.graph.library.lane import LaneEdge
from arcline.graph.library.plant import PlantNode
from arcline.graph.library.production import ProductionEdge
from arcline.graph.library.storage import StorageEdge
from arcline.graph.library.supplier import SupplierNode
from arcline.graph.library.warehouse import (
    DistributionCenterNode,
    WarehouseNode,
)

__all__ = [
    # concrete nodes
    "SupplierNode",
    "PlantNode",
    "WarehouseNode",
    "DistributionCenterNode",
    "CustomerNode",
    # concrete edges
    "LaneEdge",
    "ProductionEdge",
    "StorageEdge",
    # intermediates (for type hints & custom subclasses)
    "SourceNode",
    "FacilityNode",
    "DemandNode",
    "FlowEdge",
    "TransportEdge",
]
