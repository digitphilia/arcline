# -*- encoding: utf-8 -*-

"""
Built-in Plant Node Definition
------------------------------

A :class:`PlantNode` represents a manufacturing facility that converts
inputs into outputs at a nominal hourly rate. Capacity bounds, status,
ownership, and shift are inherited from :class:`FacilityNode`.
"""

from pydantic import Field
from typing import ClassVar, Dict, Optional

from arcline.graph.library._intermediates import FacilityNode
from arcline.graph.registry import register_node
from arcline.historian.spec import HistorySpec


class PlantNode(FacilityNode):
    """
    Concrete supply-chain node modeling a manufacturing plant.

    :param productionRatePerHr: Nominal output rate, in units / hour.
    """

    kind : ClassVar[str] = "plant"

    canManufacture : ClassVar[bool] = True

    productionRatePerHr : float = Field(
        0.0, ge = 0.0, description = "Nominal Production Rate per Hour"
    )

    history : ClassVar[Dict[str, HistorySpec]] = {
        "productionRatePerHr": HistorySpec(
            table = "fact_plant_throughput",
            schema = "dwh",
            keyColumn = "node_hash_key",
            valueColumn = "units_per_hour",
            tsColumn = "production_date",
            description = "Realized hourly throughput per production day.",
        ),
    }


    @property
    def imagePath(self) -> Optional[str]:
        """Default plant icon shipped with the package."""

        return "./icons/graph.png"


    @property
    def nodeColor(self) -> Optional[str]:
        """Default plant node color in HEX."""

        return "#42B3E3"


register_node(PlantNode)
