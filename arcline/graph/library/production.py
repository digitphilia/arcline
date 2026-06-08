# -*- encoding: utf-8 -*-

"""
Built-in Production Edge Definition
-----------------------------------

A :class:`ProductionEdge` models an intra-plant conversion step
characterized by its cycle time and yield rate. ``costPerUnit`` and
``capacityPerPeriod`` are inherited from :class:`FlowEdge`.
"""

from pydantic import Field
from typing import ClassVar, Optional

from arcline.graph.library._intermediates import FlowEdge
from arcline.graph.registry import register_edge


class ProductionEdge(FlowEdge):
    """
    Concrete supply-chain edge modeling a production / conversion arc.

    :param cycleTimeHr: Time, in hours, to complete one production
        cycle.
    :param yieldRate: Fractional yield in ``[0, 1]``; ``1.0`` denotes
        a perfect (loss-less) conversion.
    """

    kind : ClassVar[str] = "production"

    cycleTimeHr : float = Field(
        0.0, ge = 0.0, description = "Cycle Time in Hours"
    )

    yieldRate : float = Field(
        1.0, ge = 0.0, le = 1.0,
        description = "Production Yield Rate in [0, 1]"
    )


    @property
    def edgeColor(self) -> Optional[str]:
        """Default production edge color in HEX."""

        return "#9C27B0"


register_edge(ProductionEdge)
