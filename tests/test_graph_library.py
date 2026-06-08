# -*- encoding: utf-8 -*-

"""
Tests for the Built-in Supply-Chain Taxonomy
--------------------------------------------

Covers basic construction, pydantic field validation (lat/lon
bounds, lane mode literal), the DistributionCenterNode alias, and the
``model_fields`` introspection used by the dashboard's auto-form.
"""

import pytest
from pydantic import ValidationError

from arcline.graph.library import (
    CustomerNode,
    DistributionCenterNode,
    LaneEdge,
    PlantNode,
    ProductionEdge,
    StorageEdge,
    SupplierNode,
    WarehouseNode,
)


_TAXONOMY = [
    SupplierNode, PlantNode, WarehouseNode, CustomerNode, LaneEdge, ProductionEdge, StorageEdge,
]


def test_each_taxonomy_class_has_kind() -> None:
    for cls in _TAXONOMY:
        assert isinstance(cls.kind, str) and cls.kind, (
            f"{cls.__name__} must declare a non-empty `kind`."
        )


def test_supplier_construction() -> None:
    sup = SupplierNode(name = "Acme", hashKey = "N-ACME")

    assert sup.imagePath == "./icons/vendor.png"
    color = sup.nodeColor
    assert isinstance(color, str) and color.startswith("#")
    assert sup.leadTimeDays == 0.0
    assert sup.reliabilityScore == 1.0


def test_node_latitude_bounds() -> None:
    with pytest.raises(ValidationError):
        SupplierNode(name = "X", hashKey = "N-X", latitude = 95.0)

    with pytest.raises(ValidationError):
        SupplierNode(name = "X", hashKey = "N-X", latitude = -95.0)

    with pytest.raises(ValidationError):
        SupplierNode(name = "X", hashKey = "N-X", longitude = 185.0)

    with pytest.raises(ValidationError):
        SupplierNode(name = "X", hashKey = "N-X", longitude = -185.0)


def test_lane_mode_literal() -> None:
    src = SupplierNode(name = "S", hashKey = "N-S")
    dst = PlantNode(name = "P", hashKey = "N-P")

    with pytest.raises(ValidationError):
        LaneEdge(
            name = "bad", hashKey = "E-BAD",
            srcNode = src, dstNode = dst, mode = "rocket",
        )

    for mode in ("road", "rail", "sea", "air"):
        edge = LaneEdge(
            name = f"l-{mode}", hashKey = f"E-{mode.upper()}",
            srcNode = src, dstNode = dst, mode = mode,
        )
        assert edge.mode.name == mode.upper()


def test_distribution_center_alias() -> None:
    assert DistributionCenterNode is WarehouseNode


def test_pydantic_field_attrs_visible() -> None:
    assert "leadTimeDays" in SupplierNode.model_fields
    assert "reliabilityScore" in SupplierNode.model_fields
    assert "productionRatePerHr" in PlantNode.model_fields
    assert "maxCapacity" in WarehouseNode.model_fields
    assert "demandMean" in CustomerNode.model_fields
    assert "distanceKm" in LaneEdge.model_fields
    assert "costPerUnit" in LaneEdge.model_fields
    assert "cycleTimeHr" in ProductionEdge.model_fields
    assert "holdingCostPerUnit" in StorageEdge.model_fields
