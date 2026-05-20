# -*- encoding: utf-8 -*-

"""
Concrete Implementations of :class:`AbstractEdge` - Graph Edges
---------------------------------------------------------------

Exposes concrete implementations of graph edges from the base abstract
class :class:`arcline.graph.base.nodes.AbstractEdge` for calculations.
"""

from pydantic import Field
from typing import Optional

from arcline.graph.base.edges import AbstractEdge

class DefaultEdge(AbstractEdge):
    """
    A concrete default edge which is useful for any type of supply
    chain optimization and analysis.
    """

    @property
    def edgeColor(self) -> Optional[str]:
        return "#000000"
