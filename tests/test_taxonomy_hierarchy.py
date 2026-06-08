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

from pathlib import Path

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
    assert w.canShip is True
    assert w.canStore is True
    assert w.canManufacture is False
    assert w.canDemand is False


def test_capabilityFlagsCustomer() -> None:
    c = CustomerNode(name = "C", hashKey = "N-C")
    assert c.canDemand is True
    assert c.canShip is False
    assert c.canStore is False
    assert c.canManufacture is False


def test_capabilityFlagsEdges() -> None:
    s = SupplierNode(name = "S", hashKey = "N-S")
    p = PlantNode(name = "P", hashKey = "N-P")
    le = LaneEdge(
        name = "L", hashKey = "E-L", srcNode = s, dstNode = p
    )
    assert le.carriesProduct is True
    assert le.carriesInfo is False
    assert le.supports("carriesProduct") is True


def test_capabilityFlagsProductionEdge() -> None:
    p = PlantNode(name = "P", hashKey = "N-P")
    pe = ProductionEdge(
        name = "PE", hashKey = "E-PE", srcNode = p, dstNode = p
    )
    assert pe.carriesProduct is True
    assert pe.carriesInfo is False
    assert pe.supports("carriesProduct") is True
    assert not isinstance(pe, TransportEdge)


def test_capabilityFlagsStorageEdge() -> None:
    w = WarehouseNode(name = "W", hashKey = "N-W")
    se = StorageEdge(
        name = "SE", hashKey = "E-SE", srcNode = w, dstNode = w,
    )
    assert se.carriesProduct is True
    assert se.carriesInfo is False
    assert se.supports("carriesProduct") is True
    assert not isinstance(se, TransportEdge)


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


def test_facilityCapacityBoundsAcceptTypical() -> None:
    w = WarehouseNode(
        name = "W", hashKey = "N-W",
        minCapacity = 100.0, maxCapacity = 5000.0,
    )
    assert w.minCapacity == 100.0
    assert w.maxCapacity == 5000.0


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


# ---------- writer hardening: non-finite float defaults -----------------------


def test_writerSanitisesInfiniteDefaults(tmp_path : Path) -> None:
    """
    ``capacityPerPeriod`` and other ``math.inf`` field defaults must
    be serialised as JSON ``null`` so the resulting files are
    consumable by strict parsers (``json.loads(..., allow_nan=False)``,
    browser ``JSON.parse``, ``jq``, BigQuery). The writer rewrites
    non-finite floats to ``None`` before ``json.dump``.
    """

    import json

    from arcline.graph.builder import NetworkBuilder
    from arcline.io import Project

    builder = NetworkBuilder()
    s = builder.add(SupplierNode(name = "S", hashKey = "N-S"))
    p = builder.add(PlantNode(name = "P", hashKey = "N-P"))
    builder.connect(
        s, p, cls = LaneEdge,
        name = "S->P", hashKey = "E-SP",
        distanceKm = 100.0, transitDays = 1.0,
        mode = TransportationMode.ROAD,
    )

    graph = builder.build(backend = "networkx")
    proj = Project.fromGraph(
        graph, path = tmp_path / "infproj", name = "infproj",
    )
    proj.save()

    raw = (tmp_path / "infproj" / "edges.json").read_text(
        encoding = "utf-8"
    )
    parsed = json.loads(raw)
    assert parsed[0]["capacityPerPeriod"] is None
    assert "Infinity" not in raw

    nodesRaw = (tmp_path / "infproj" / "nodes.json").read_text(
        encoding = "utf-8"
    )
    assert "Infinity" not in nodesRaw


# ---------- full-taxonomy integration round-trip -----------------------------


def test_fullTaxonomyProjectRoundTrip(tmp_path : Path) -> None:
    """
    Build a network covering ALL four node kinds and ALL three edge
    kinds, persist it as a project, re-open it, and verify every kind
    discriminator and capability flag survives the round-trip.
    """

    from arcline.graph.builder import NetworkBuilder
    from arcline.io import Project

    builder = NetworkBuilder()

    sup = builder.add(SupplierNode(
        name = "Sup", hashKey = "N-SUP", leadTimeDays = 3.0,
    ))
    plt = builder.add(PlantNode(
        name = "Plt", hashKey = "N-PLT",
        minCapacity = 10.0, maxCapacity = 10_000.0,
    ))
    wh = builder.add(WarehouseNode(
        name = "Wh", hashKey = "N-WH",
        minCapacity = 0.0, maxCapacity = 25_000.0,
    ))
    cust = builder.add(CustomerNode(
        name = "Cust", hashKey = "N-CUST",
        demandMean = 100.0, demandStd = 15.0,
    ))

    builder.connect(
        sup, plt, cls = LaneEdge,
        name = "Sup->Plt", hashKey = "E-SP",
        distanceKm = 220.0, costPerUnit = 2.5, transitDays = 1.5,
        mode = TransportationMode.ROAD,
    )
    builder.connect(
        plt, plt, cls = ProductionEdge,
        name = "Plt-prod", hashKey = "E-PP",
        costPerUnit = 0.8,
    )
    builder.connect(
        plt, wh, cls = LaneEdge,
        name = "Plt->Wh", hashKey = "E-PW",
        distanceKm = 15.0, costPerUnit = 0.4, transitDays = 0.2,
        mode = TransportationMode.RAIL,
        serviceLevel = LaneServiceLevel.EXPEDITED,
    )
    builder.connect(
        wh, wh, cls = StorageEdge,
        name = "Wh-store", hashKey = "E-WS",
        storageType = StorageType.COLD_CHAIN,
    )
    builder.connect(
        wh, cust, cls = LaneEdge,
        name = "Wh->Cust", hashKey = "E-WC",
        distanceKm = 40.0, costPerUnit = 1.1, transitDays = 0.5,
        mode = TransportationMode.ROAD,
    )

    graph = builder.build(backend = "networkx")

    proj = Project.fromGraph(
        graph, path = tmp_path / "full_taxonomy",
        name = "full-taxonomy",
    )
    proj.save()

    reopened = Project.open(tmp_path / "full_taxonomy")
    reopenedGraph = reopened.toGraph()

    nodesByKey = {n.hashKey: n for n in reopenedGraph.nodes}
    edgesByKey = {e.hashKey: e for e in reopenedGraph.edges}

    assert isinstance(nodesByKey["N-SUP"], SupplierNode)
    assert isinstance(nodesByKey["N-PLT"], PlantNode)
    assert isinstance(nodesByKey["N-WH"],  WarehouseNode)
    assert isinstance(nodesByKey["N-CUST"], CustomerNode)

    assert isinstance(edgesByKey["E-SP"], LaneEdge)
    assert isinstance(edgesByKey["E-PP"], ProductionEdge)
    assert isinstance(edgesByKey["E-PW"], LaneEdge)
    assert isinstance(edgesByKey["E-WS"], StorageEdge)
    assert isinstance(edgesByKey["E-WC"], LaneEdge)

    # Enum round-trip survived
    assert edgesByKey["E-PW"].mode is TransportationMode.RAIL
    assert edgesByKey["E-PW"].serviceLevel is LaneServiceLevel.EXPEDITED
    assert edgesByKey["E-WS"].storageType is StorageType.COLD_CHAIN

    # Capability flags survive
    assert nodesByKey["N-PLT"].supports("canManufacture") is True
    assert nodesByKey["N-WH"].supports("canManufacture") is False
    assert edgesByKey["E-PP"].supports("carriesProduct") is True
