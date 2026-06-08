# -*- encoding: utf-8 -*-

"""
Built-in Storage Edge Definition
--------------------------------

A :class:`StorageEdge` models inventory-holding time at a node, with a
per-unit holding cost and an upper bound on hold duration.
``costPerUnit`` and ``capacityPerPeriod`` are inherited from
:class:`FlowEdge`.
"""

from pydantic import Field
from typing import ClassVar, Optional

from arcline.graph.enums import StorageType
from arcline.graph.library._intermediates import FlowEdge
from arcline.graph.registry import register_edge


class StorageEdge(FlowEdge):
    """
    Concrete supply-chain edge modeling an inventory-holding arc.

    :param holdingCostPerUnit: Per-unit holding cost charged while
        the inventory remains in storage.
    :param maxHoldDays: Maximum number of days the inventory may be
        held; defaults to ``None`` (no upper limit).
    :param storageType: Climate / handling regime for stored product;
        defaults to :attr:`StorageType.AMBIENT`.
    """

    kind : ClassVar[str] = "storage"

    holdingCostPerUnit : float = Field(
        0.0, ge = 0.0, description = "Per-Unit Holding Cost"
    )

    maxHoldDays : Optional[float] = Field(
        None, gt = 0.0,
        description = "Maximum Hold Duration in Days (None = unbounded)"
    )

    storageType : StorageType = Field(
        default = StorageType.AMBIENT,
        description = "Climate / Handling Regime",
    )


    @property
    def edgeColor(self) -> Optional[str]:
        """Default storage edge color in HEX."""

        return "#795548"


register_edge(StorageEdge)
