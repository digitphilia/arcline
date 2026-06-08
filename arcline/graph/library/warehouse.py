# -*- encoding: utf-8 -*-

"""
Built-in Warehouse / Distribution-Center Node Definition
--------------------------------------------------------

A :class:`WarehouseNode` represents an inventory-holding facility (also
known as a Distribution Center, exposed under the alias
:data:`DistributionCenterNode`). Capacity bounds, status, ownership,
and shift are inherited from :class:`FacilityNode`.
"""

from pydantic import Field
from typing import ClassVar, Dict, Optional

from arcline.graph.enums import StorageType
from arcline.graph.library._intermediates import FacilityNode
from arcline.graph.registry import register_node
from arcline.historian.spec import HistorySpec


class WarehouseNode(FacilityNode):
    """
    Concrete supply-chain node modeling an inventory-holding facility.

    :param storageType: Climate / handling regime for stored product;
        defaults to :attr:`StorageType.AMBIENT`.
    """

    kind : ClassVar[str] = "warehouse"

    storageType : StorageType = Field(
        default = StorageType.AMBIENT,
        description = "Climate / Handling Regime",
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
        """Default warehouse icon shipped with the package."""

        return "./icons/warehouse.png"


    @property
    def nodeColor(self) -> Optional[str]:
        """Default warehouse node color in HEX."""

        return "#7BC47F"


# Distribution Center is an alias of Warehouse - shares the same kind
# and is intentionally not registered separately.
DistributionCenterNode = WarehouseNode

register_node(WarehouseNode)
