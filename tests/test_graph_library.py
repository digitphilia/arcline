# -*- encoding: utf-8 -*-

"""
Tests for the Built-in Supply-Chain Taxonomy
--------------------------------------------

Covers basic construction, pydantic field validation (lat/lon
bounds, lane mode literal), the DistributionCenter alias, and the
``model_fields`` introspection used by the dashboard's auto-form.
"""

import pytest
from pydantic import ValidationError

from arcline.graph.library import (
    Customer,
    DistributionCenter,
    Lane,
    Plant,
    Production,
    Storage,
    Supplier,
    Warehouse,
)


_TAXONOMY = [
    Supplier, Plant, Warehouse, Customer, Lane, Production, Storage,
]


def test_each_taxonomy_class_has_kind() -> None:
    for cls in _TAXONOMY:
        assert isinstance(cls.kind, str) and cls.kind, (
            f"{cls.__name__} must declare a non-empty `kind`."
        )


def test_supplier_construction() -> None:
    sup = Supplier(name = "Acme", hashKey = "N-ACME")

    assert sup.imagePath == "./icons/vendor.png"
    color = sup.nodeColor
    assert isinstance(color, str) and color.startswith("#")
    assert sup.leadTimeDays == 0.0
    assert sup.reliabilityScore == 1.0


def test_node_latitude_bounds() -> None:
    with pytest.raises(ValidationError):
        Supplier(name = "X", hashKey = "N-X", latitude = 95.0)

    with pytest.raises(ValidationError):
        Supplier(name = "X", hashKey = "N-X", latitude = -95.0)

    with pytest.raises(ValidationError):
        Supplier(name = "X", hashKey = "N-X", longitude = 185.0)

    with pytest.raises(ValidationError):
        Supplier(name = "X", hashKey = "N-X", longitude = -185.0)


def test_lane_mode_literal() -> None:
    src = Supplier(name = "S", hashKey = "N-S")
    dst = Plant(name = "P", hashKey = "N-P")

    with pytest.raises(ValidationError):
        Lane(
            name = "bad", hashKey = "E-BAD",
            srcNode = src, dstNode = dst, mode = "rocket",
        )

    for mode in ("road", "rail", "sea", "air"):
        edge = Lane(
            name = f"l-{mode}", hashKey = f"E-{mode.upper()}",
            srcNode = src, dstNode = dst, mode = mode,
        )
        assert edge.mode == mode


def test_distribution_center_alias() -> None:
    assert DistributionCenter is Warehouse


def test_pydantic_field_attrs_visible() -> None:
    assert "leadTimeDays" in Supplier.model_fields
    assert "reliabilityScore" in Supplier.model_fields
    assert "productionRatePerHr" in Plant.model_fields
    assert "maxCapacity" in Warehouse.model_fields
    assert "demandMean" in Customer.model_fields
    assert "distanceKm" in Lane.model_fields
    assert "costPerUnit" in Lane.model_fields
    assert "cycleTimeHr" in Production.model_fields
    assert "holdingCostPerUnit" in Storage.model_fields
