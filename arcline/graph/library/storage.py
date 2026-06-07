# -*- encoding: utf-8 -*-

"""
Built-in Storage Edge Definition
--------------------------------

A :class:`Storage` edge models inventory-holding time at a node, with
a per-unit holding cost and an upper bound on hold duration.
"""

from pydantic import Field
from typing import ClassVar, Optional

from arcline.graph.base.edges import AbstractEdge
from arcline.graph.registry import register_edge


class Storage(AbstractEdge):
    """
    Concrete supply-chain edge modeling an inventory-holding arc.

    :param holdingCostPerUnit: Per-unit holding cost charged while
        the inventory remains in storage.
    :param maxHoldDays: Maximum number of days the inventory may be
        held; defaults to no limit (``inf``).
    """

    kind : ClassVar[str] = "storage"

    holdingCostPerUnit : float = Field(
        0.0, ge = 0.0, description = "Per-Unit Holding Cost"
    )

    maxHoldDays : float = Field(
        float("inf"), gt = 0.0,
        description = "Maximum Hold Duration in Days"
    )


    @property
    def edgeColor(self) -> Optional[str]:
        """
        Default storage edge color in HEX.
        """

        return "#795548"


register_edge(Storage)
