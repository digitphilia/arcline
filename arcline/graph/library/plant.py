# -*- encoding: utf-8 -*-

"""
Built-in Plant Node Definition
------------------------------

A :class:`Plant` represents a manufacturing facility that converts
inputs into outputs at a nominal hourly rate, bounded by minimum and
maximum throughput capacities.
"""

from pydantic import Field
from typing import ClassVar, Dict, Optional

from arcline.graph.base.nodes import AbstractNode
from arcline.graph.registry import register_node
from arcline.historian.spec import HistorySpec


class Plant(AbstractNode):
    """
    Concrete supply-chain node modeling a manufacturing plant with
    a nominal hourly production rate and capacity bounds.

    :param productionRatePerHr: Nominal output rate, in units / hour.
    :param minCapacity: Lower bound of the operational throughput.
    :param maxCapacity: Upper bound of the operational throughput.
    """

    kind : ClassVar[str] = "plant"

    productionRatePerHr : float = Field(
        0.0, ge = 0.0, description = "Nominal Production Rate per Hour"
    )

    minCapacity : float = Field(
        0.0, ge = 0.0, description = "Min. Capacity of the Plant"
    )

    maxCapacity : float = Field(
        float("inf"), gt = 0.0,
        description = "Max. Capacity of the Plant"
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
        """
        Default plant icon shipped with the package.
        """

        return "./icons/graph.png"


    @property
    def nodeColor(self) -> Optional[str]:
        """
        Default plant node color in HEX.
        """

        return "#42B3E3"


register_node(Plant)
