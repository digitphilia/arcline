# -*- encoding: utf-8 -*-

"""
Abstract Intermediate Node & Edge Bases
---------------------------------------

Concrete supply-chain classes share a meaningful amount of structure -
e.g. every facility (plant, warehouse, distribution centre) carries a
``minCapacity`` / ``maxCapacity`` pair, an :class:`OwnershipType`, an
:class:`OperationalShift`, and a :class:`FacilityStatus`; every flow
edge carries a ``costPerUnit`` and a ``capacityPerPeriod``. Hoisting
those fields onto small abstract intermediate classes keeps the
concrete ``*Node`` / ``*Edge`` files focused on their own
distinguishing attributes (DRY).

The intermediates are **abstract**: they intentionally do *not*
implement the abstract :attr:`AbstractNode.imagePath` /
:attr:`AbstractNode.nodeColor` (or the analogous edge property), and
they are *not* registered with :mod:`arcline.graph.registry`. Only
the leaf concrete classes call :func:`register_node` /
:func:`register_edge`.
"""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field, model_validator

from arcline.graph.base.edges import AbstractEdge
from arcline.graph.base.nodes import AbstractNode
from arcline.graph.enums import (
    FacilityStatus,
    OperationalShift,
    OwnershipType,
    TransportationMode,
)


class SourceNode(AbstractNode):
    """
    Abstract base for upstream supply nodes that *originate* product
    (e.g. :class:`SupplierNode`). A source node ships outbound, does
    not store inventory, does not manufacture, and does not absorb
    demand.
    """

    canShip        : ClassVar[bool] = True
    canStore       : ClassVar[bool] = False
    canManufacture : ClassVar[bool] = False
    canDemand      : ClassVar[bool] = False


class DemandNode(AbstractNode):
    """
    Abstract base for downstream demand nodes that *consume* product
    (e.g. :class:`CustomerNode`). A demand node absorbs demand, does
    not ship, store, or manufacture by default.
    """

    canShip        : ClassVar[bool] = False
    canStore       : ClassVar[bool] = False
    canManufacture : ClassVar[bool] = False
    canDemand      : ClassVar[bool] = True


class FacilityNode(AbstractNode):
    """
    Abstract base for physical facilities (plants, warehouses,
    distribution centres) sharing capacity bounds, ownership, shift
    pattern, and operational status.

    :param minCapacity: Lower bound of operational throughput / holding
        capacity (units, non-negative).
    :param maxCapacity: Upper bound of operational throughput / holding
        capacity (units, strictly positive); defaults to ``inf``.
    :param operatingCostPerHr: Fixed operating cost per hour while the
        facility is open (currency-agnostic; non-negative).
    :param status: Operational lifecycle state; defaults to ``OPEN``.
    :param ownership: Asset ownership pattern; defaults to ``OWNED``.
    :param shift: Active shift pattern; defaults to ``DAY``.
    """

    canShip        : ClassVar[bool] = True
    canStore       : ClassVar[bool] = True
    canManufacture : ClassVar[bool] = False
    canDemand      : ClassVar[bool] = False

    minCapacity : float = Field(
        0.0, ge = 0.0,
        description = "Min. Operational Capacity",
    )

    maxCapacity : float = Field(
        float("inf"), gt = 0.0,
        description = "Max. Operational Capacity",
    )

    operatingCostPerHr : float = Field(
        0.0, ge = 0.0,
        description = "Fixed Operating Cost per Hour",
    )

    status : FacilityStatus = Field(
        default = FacilityStatus.OPEN,
        description = "Operational Lifecycle Status",
    )

    ownership : OwnershipType = Field(
        default = OwnershipType.OWNED,
        description = "Asset Ownership Pattern",
    )

    shift : OperationalShift = Field(
        default = OperationalShift.DAY,
        description = "Active Operational Shift",
    )

    @model_validator(mode = "after")
    def _validateCapacityBounds(self) -> "FacilityNode":
        """
        Enforce ``minCapacity <= maxCapacity`` after field
        validation. Inherited verbatim by every concrete facility
        subclass so the rule lives in exactly one place.
        """

        if self.minCapacity > self.maxCapacity:
            raise ValueError(
                f"minCapacity ({self.minCapacity}) must be "
                f"<= maxCapacity ({self.maxCapacity}) on "
                f"{type(self).__name__}."
            )
        return self


class FlowEdge(AbstractEdge):
    """
    Abstract base for edges that *carry product* between two nodes.

    :param costPerUnit: Variable cost charged per unit of product
        traversing the edge (non-negative).
    :param capacityPerPeriod: Upper bound on units carried per
        scheduling period; defaults to ``inf``.
    """

    carriesProduct : ClassVar[bool] = True
    carriesInfo    : ClassVar[bool] = False

    costPerUnit : float = Field(
        0.0, ge = 0.0,
        description = "Variable Unit Cost on the Edge",
    )

    capacityPerPeriod : float = Field(
        float("inf"), gt = 0.0,
        description = "Upper Bound on Units per Period",
    )


class TransportEdge(FlowEdge):
    """
    Abstract base for *transportation* edges (road, rail, sea, air).

    :param mode: Transport modality; one of :class:`TransportationMode`.
    :param transitDays: Nominal door-to-door transit time, in days.
    """

    mode : TransportationMode = Field(
        default = TransportationMode.ROAD,
        description = "Transportation Mode",
    )

    transitDays : float = Field(
        0.0, ge = 0.0,
        description = "Nominal Transit Time in Days",
    )


__all__ = [
    "SourceNode",
    "DemandNode",
    "FacilityNode",
    "FlowEdge",
    "TransportEdge",
]
