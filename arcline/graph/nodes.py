# -*- encoding: utf-8 -*-

"""
Concrete Implementations of :class:`AbstractNode` - Graph Nodes
---------------------------------------------------------------

Exposes concrete implementations of graph nodes from the base abstract
class :class:`arcline.graph.base.nodes.AbstractNode` for calculations.
"""

from pydantic import Field
from typing import Optional

from arcline.graph.base.nodes import AbstractNode

class DefaultNode(AbstractNode):
    """
    A concrete default node which is useful for any type of supply
    chain optimization and analysis. The node captures the "capacity"
    which is typically inherent for solving complex problems and
    are always a hard constraint in the cost function.
    """

    minCapacity : float = Field(
        0.00, gt = 0.00, description = "Min. Capacity of the Node"
    )

    maxCapacity : float = Field(
        float("inf"), gt = 0.00, description = "Max. Capacity of the Node"
    )


    @property
    def imagePath(self) -> Optional[str]:
        return "./icons/graph.png"


    @property
    def nodeColor(self) -> Optional[str]:
        return "#42B3E3"
