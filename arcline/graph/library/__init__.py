# -*- encoding: utf-8 -*-

"""
Built-in Supply-Chain Taxonomy
==============================

Concrete subclasses of :class:`arcline.graph.base.AbstractNode` and
:class:`arcline.graph.base.AbstractEdge` shipped with the package.
Importing this subpackage triggers the registry side-effects that
make every shipped ``kind`` resolvable via
:mod:`arcline.graph.registry`.
"""

from arcline.graph.library.supplier import Supplier
from arcline.graph.library.plant import Plant
from arcline.graph.library.warehouse import Warehouse, DistributionCenter
from arcline.graph.library.customer import Customer
from arcline.graph.library.lane import Lane
from arcline.graph.library.production import Production
from arcline.graph.library.storage import Storage

__all__ = [
    "Supplier",
    "Plant",
    "Warehouse",
    "DistributionCenter",
    "Customer",
    "Lane",
    "Production",
    "Storage",
]
