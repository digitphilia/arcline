# -*- encoding: utf-8 -*-

"""
Built-in Warehouse / Distribution-Center Node Definition
--------------------------------------------------------

A :class:`Warehouse` represents an inventory-holding facility (also
known as a Distribution Center, exposed under the alias
:data:`DistributionCenter`).
"""

from pydantic import Field
from typing import ClassVar, Dict, Optional

from arcline.graph.base.nodes import AbstractNode
from arcline.graph.registry import register_node
from arcline.historian.spec import HistorySpec


class Warehouse(AbstractNode):
    """
    Concrete supply-chain node modeling an inventory-holding facility
    bounded by minimum and maximum storage capacities.

    :param minCapacity: Lower bound of the holding capacity.
    :param maxCapacity: Upper bound of the holding capacity.
    """

    kind : ClassVar[str] = "warehouse"

    minCapacity : float = Field(
        0.0, ge = 0.0, description = "Min. Capacity of the Warehouse"
    )

    maxCapacity : float = Field(
        float("inf"), gt = 0.0,
        description = "Max. Capacity of the Warehouse"
    )

    history : ClassVar[Dict[str, HistorySpec]] = {
        "maxCapacity": HistorySpec(
            table = "fact_warehouse_throughput",
            schema = "dwh",
            keyColumn = "node_hash_key",
            valueColumn = "units_handled",
            tsColumn = "activity_date",
            description = "Daily throughput observed at the warehouse.",
        ),
    }


    @property
    def imagePath(self) -> Optional[str]:
        """
        Default warehouse icon shipped with the package.
        """

        return "./icons/warehouse.png"


    @property
    def nodeColor(self) -> Optional[str]:
        """
        Default warehouse node color in HEX.
        """

        return "#7BC47F"


# Distribution Center is an alias of Warehouse - shares the same kind
# and is intentionally not registered separately.
DistributionCenter = Warehouse

register_node(Warehouse)
