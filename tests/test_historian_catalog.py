# -*- encoding: utf-8 -*-

"""
Phase 1.5 - P15-5 (built-in catalog) tests.
"""

from __future__ import annotations

from arcline.historian import HistorySpec, specFor, attributesFor, iterCatalog
from arcline.graph.library import (
    CustomerNode, LaneEdge, PlantNode, WarehouseNode,
)


def test_lane_hasTransitDaysAndCostHistory():
    assert "transitDays" in LaneEdge.history
    assert "costPerUnit" in LaneEdge.history
    spec = LaneEdge.history["transitDays"]
    assert isinstance(spec, HistorySpec)
    assert spec.qualifiedTable() == "dwh.fact_lane_lead_time"


def test_plant_warehouse_customer_haveHistory():
    assert "productionRatePerHr" in PlantNode.history
    assert "maxCapacity" in WarehouseNode.history
    assert "demandMean" in CustomerNode.history


def test_specFor_lookup():
    spec = specFor("lane", "transitDays")
    assert spec is not None
    assert spec.valueColumn == "actual_lead_time_days"


def test_specFor_unknownKindReturnsNone():
    assert specFor("nonexistent", "x") is None


def test_specFor_unknownAttributeReturnsNone():
    assert specFor("lane", "nonexistent") is None


def test_attributesFor_lane():
    attrs = attributesFor("lane")
    assert "transitDays" in attrs
    assert "costPerUnit" in attrs


def test_iterCatalog_includesAllBuiltins():
    catalog = list(iterCatalog())
    kinds = {k for k, _, _ in catalog}
    assert {"lane", "plant", "warehouse", "customer"}.issubset(kinds)
    for kind, attr, spec in catalog:
        assert isinstance(spec, HistorySpec)
        assert isinstance(attr, str)


def test_specHash_isStableAcrossInstances():
    spec1 = LaneEdge.history["transitDays"]
    spec2 = LaneEdge.history["transitDays"]
    assert spec1.specHash() == spec2.specHash()
