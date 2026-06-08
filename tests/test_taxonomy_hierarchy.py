# -*- encoding: utf-8 -*-

"""
Tests for the Phase 1.6 taxonomy hierarchy
==========================================

Covers the abstract intermediates (:class:`FacilityNode`,
:class:`SourceNode`, :class:`DemandNode`, :class:`FlowEdge`,
:class:`TransportEdge`), the capability flags that drive downstream
tooling, the cross-field validators inherited via the intermediates,
and registry hygiene (intermediates must NOT be registered).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from arcline.graph.enums import (
    CustomerSegment,
    FacilityStatus,
    LaneServiceLevel,
    OperationalShift,
    OwnershipType,
    StorageType,
    TransportationMode,
)
from arcline.graph.library import (
    CustomerNode,
    DemandNode,
    DistributionCenterNode,
    FacilityNode,
    FlowEdge,
    LaneEdge,
    PlantNode,
    ProductionEdge,
    SourceNode,
    StorageEdge,
    SupplierNode,
    TransportEdge,
    WarehouseNode,
)
from arcline.graph.registry import iter_edges, iter_nodes


# ---------- isinstance chain --------------------------------------------------


def test_inheritanceChainNodes() -> None:
    s = SupplierNode(name = "S", hashKey = "N-S")
    p = PlantNode(name = "P", hashKey = "N-P")
    w = WarehouseNode(name = "W", hashKey = "N-W")
    c = CustomerNode(name = "C", hashKey = "N-C")

    assert isinstance(s, SourceNode)
    assert isinstance(p, FacilityNode)
    assert isinstance(w, FacilityNode)
    assert isinstance(c, DemandNode)


def test_inheritanceChainEdges() -> None:
    s = SupplierNode(name = "S", hashKey = "N-S")
    p = PlantNode(name = "P", hashKey = "N-P")
    le = LaneEdge(
        name = "L", hashKey = "E-L", srcNode = s, dstNode = p
    )
    pe = ProductionEdge(
        name = "PE", hashKey = "E-PE", srcNode = p, dstNode = p
    )
    se = StorageEdge(
        name = "SE", hashKey = "E-SE", srcNode = p, dstNode = p
    )

    assert isinstance(le, TransportEdge)
    assert isinstance(le, FlowEdge)
    assert isinstance(pe, FlowEdge)
    assert isinstance(se, FlowEdge)
    assert not isinstance(pe, TransportEdge)


# ---------- capability flags --------------------------------------------------


def test_capabilityFlagsPlant() -> None:
    p = PlantNode(name = "P", hashKey = "N-P")
    assert p.canShip is True
    assert p.canStore is True
    assert p.canManufacture is True
    assert p.canDemand is False
    assert p.supports("canManufacture") is True
    assert p.supports("canDemand") is False
    assert p.supports("nonsense") is False


def test_capabilityFlagsSupplier() -> None:
    s = SupplierNode(name = "S", hashKey = "N-S")
    assert s.canShip is True
    assert s.canStore is False
    assert s.canManufacture is False
    assert s.canDemand is False


def test_capabilityFlagsWarehouse() -> None:
    w = WarehouseNode(name = "W", hashKey = "N-W")
    assert w.canStore is True
    assert w.canManufacture is False


def test_capabilityFlagsCustomer() -> None:
    c = CustomerNode(name = "C", hashKey = "N-C")
    assert c.canDemand is True
    assert c.canShip is False


def test_capabilityFlagsEdges() -> None:
    s = SupplierNode(name = "S", hashKey = "N-S")
    p = PlantNode(name = "P", hashKey = "N-P")
    le = LaneEdge(
        name = "L", hashKey = "E-L", srcNode = s, dstNode = p
    )
    assert le.carriesProduct is True
    assert le.carriesInfo is False
    assert le.supports("carriesProduct") is True


# ---------- cross-field validator ---------------------------------------------


def test_facilityCapacityBoundsRejectInverted() -> None:
    with pytest.raises(ValidationError):
        PlantNode(
            name = "P", hashKey = "N-P",
            minCapacity = 100.0, maxCapacity = 10.0,
        )


def test_facilityCapacityBoundsAcceptEqual() -> None:
    p = PlantNode(
        name = "P", hashKey = "N-P",
        minCapacity = 50.0, maxCapacity = 50.0,
    )
    assert p.minCapacity == 50.0
    assert p.maxCapacity == 50.0


# ---------- enum field defaults -----------------------------------------------


def test_facilityEnumDefaults() -> None:
    p = PlantNode(name = "P", hashKey = "N-P")
    assert p.status is FacilityStatus.OPEN
    assert p.ownership is OwnershipType.OWNED
    assert p.shift is OperationalShift.DAY


def test_warehouseStorageTypeDefault() -> None:
    w = WarehouseNode(name = "W", hashKey = "N-W")
    assert w.storageType is StorageType.AMBIENT


def test_customerSegmentDefault() -> None:
    c = CustomerNode(name = "C", hashKey = "N-C")
    assert c.segment is CustomerSegment.RETAIL


def test_laneEnumDefaults() -> None:
    s = SupplierNode(name = "S", hashKey = "N-S")
    p = PlantNode(name = "P", hashKey = "N-P")
    le = LaneEdge(
        name = "L", hashKey = "E-L", srcNode = s, dstNode = p
    )
    assert le.mode is TransportationMode.ROAD
    assert le.serviceLevel is LaneServiceLevel.STANDARD


# ---------- registry hygiene --------------------------------------------------


def test_registeredNodeKindsExactlyFour() -> None:
    kinds = sorted(k for k, _ in iter_nodes())
    assert kinds == ["customer", "plant", "supplier", "warehouse"]


def test_registeredEdgeKindsExactlyThree() -> None:
    kinds = sorted(k for k, _ in iter_edges())
    assert kinds == ["lane", "production", "storage"]


def test_intermediatesNotRegistered() -> None:
    classes = {cls for _, cls in iter_nodes()}
    classes |= {cls for _, cls in iter_edges()}
    for intermediate in (
        SourceNode, FacilityNode, DemandNode, FlowEdge, TransportEdge
    ):
        assert intermediate not in classes, (
            f"{intermediate.__name__} must not be registered."
        )


def test_distributionCenterAlias() -> None:
    assert DistributionCenterNode is WarehouseNode
